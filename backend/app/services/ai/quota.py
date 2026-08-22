"""Transactional daily and credit-balance controls for AI calls."""

from dataclasses import dataclass
from datetime import date, datetime, timezone
import uuid
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.ai import AiProjectDailyUsage, AiUsageEvent, AiUserDailyUsage, AiUserQuota
from app.models.user import User


class AiQuotaExceededError(Exception):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class QuotaSnapshot:
    plan_code: str
    daily_limit: int
    daily_used: int
    daily_remaining: int
    credit_balance: int
    project_daily_limit: int
    project_daily_used: int
    project_daily_remaining: int


def current_usage_date() -> date:
    """Quota day follows the platform's primary operating timezone."""
    return datetime.now(ZoneInfo("Asia/Shanghai")).date()


def _quota(db: Session, user_id, *, lock: bool = False) -> AiUserQuota | None:
    statement = select(AiUserQuota).where(AiUserQuota.user_id == user_id)
    if lock:
        statement = statement.with_for_update()
    return db.scalar(statement)


def _is_postgresql(db: Session) -> bool:
    return db.get_bind().dialect.name == "postgresql"


def ensure_user_quota(db: Session, user_id, *, lock: bool = False) -> AiUserQuota:
    quota = _quota(db, user_id, lock=lock)
    if quota is not None:
        return quota
    settings = get_settings()
    if _is_postgresql(db):
        # INSERT ... ON CONFLICT makes a first request from two browser tabs safe.
        db.execute(
            pg_insert(AiUserQuota)
            .values(
                id=uuid.uuid4(),
                user_id=user_id,
                plan_code="basic",
                daily_limit=settings.ai_default_daily_user_limit,
                credit_balance=settings.ai_default_credit_balance,
            )
            .on_conflict_do_nothing(index_elements=["user_id"])
        )
        return _quota(db, user_id, lock=lock)  # type: ignore[return-value]
    quota = AiUserQuota(
        user_id=user_id,
        plan_code="basic",
        daily_limit=settings.ai_default_daily_user_limit,
        credit_balance=settings.ai_default_credit_balance,
    )
    db.add(quota)
    db.flush()
    return quota


def _user_daily_usage(db: Session, user_id, usage_date: date, *, lock: bool = False) -> AiUserDailyUsage:
    statement = select(AiUserDailyUsage).where(
        AiUserDailyUsage.user_id == user_id,
        AiUserDailyUsage.usage_date == usage_date,
    )
    if lock:
        statement = statement.with_for_update()
    usage = db.scalar(statement)
    if usage is None:
        if _is_postgresql(db):
            db.execute(
                pg_insert(AiUserDailyUsage)
                .values(id=uuid.uuid4(), user_id=user_id, usage_date=usage_date, calls_used=0)
                .on_conflict_do_nothing(index_elements=["user_id", "usage_date"])
            )
            return db.scalar(statement)  # type: ignore[return-value]
        usage = AiUserDailyUsage(user_id=user_id, usage_date=usage_date, calls_used=0)
        db.add(usage)
        db.flush()
    return usage


def _project_daily_usage(db: Session, usage_date: date, *, lock: bool = False) -> AiProjectDailyUsage:
    statement = select(AiProjectDailyUsage).where(AiProjectDailyUsage.usage_date == usage_date)
    if lock:
        statement = statement.with_for_update()
    usage = db.scalar(statement)
    if usage is None:
        if _is_postgresql(db):
            # All users converge on this one row, then SELECT FOR UPDATE serializes
            # reservations against the immutable project-wide environment ceiling.
            db.execute(
                pg_insert(AiProjectDailyUsage)
                .values(id=uuid.uuid4(), usage_date=usage_date, calls_used=0)
                .on_conflict_do_nothing(index_elements=["usage_date"])
            )
            return db.scalar(statement)  # type: ignore[return-value]
        usage = AiProjectDailyUsage(usage_date=usage_date, calls_used=0)
        db.add(usage)
        db.flush()
    return usage


def quota_snapshot(db: Session, user_id) -> QuotaSnapshot:
    usage_date = current_usage_date()
    quota = ensure_user_quota(db, user_id)
    user_usage = _user_daily_usage(db, user_id, usage_date)
    project_usage = _project_daily_usage(db, usage_date)
    settings = get_settings()
    daily_remaining = max(0, min(quota.daily_limit - user_usage.calls_used, quota.credit_balance))
    return QuotaSnapshot(
        plan_code=quota.plan_code,
        daily_limit=quota.daily_limit,
        daily_used=user_usage.calls_used,
        daily_remaining=daily_remaining,
        credit_balance=quota.credit_balance,
        project_daily_limit=settings.ai_daily_project_limit,
        project_daily_used=project_usage.calls_used,
        project_daily_remaining=max(0, settings.ai_daily_project_limit - project_usage.calls_used),
    )


def reserve_ai_call(db: Session, user: User, conversation_id) -> AiUsageEvent:
    """Reserve exactly one call before reaching the provider.

    The rows are locked in a stable order, so concurrent requests cannot exceed either
    the per-user daily ceiling or the project-wide environment-controlled ceiling.
    """
    usage_date = current_usage_date()
    quota = ensure_user_quota(db, user.id, lock=True)
    user_usage = _user_daily_usage(db, user.id, usage_date, lock=True)
    project_usage = _project_daily_usage(db, usage_date, lock=True)
    settings = get_settings()
    if quota.credit_balance <= 0:
        raise AiQuotaExceededError("credit_balance_exhausted")
    if user_usage.calls_used >= quota.daily_limit:
        raise AiQuotaExceededError("user_daily_limit_reached")
    if project_usage.calls_used >= settings.ai_daily_project_limit:
        raise AiQuotaExceededError("project_daily_limit_reached")

    user_usage.calls_used += 1
    project_usage.calls_used += 1
    quota.credit_balance -= 1
    event = AiUsageEvent(
        tenant_id=user.tenant_id,
        user_id=user.id,
        conversation_id=conversation_id,
        usage_date=usage_date,
        model=settings.minimax_model,
        status="reserved",
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def complete_ai_call(db: Session, event_id, *, input_tokens: int | None, output_tokens: int | None) -> None:
    event = db.scalar(select(AiUsageEvent).where(AiUsageEvent.id == event_id).with_for_update())
    if event is None or event.status != "reserved":
        return
    event.status = "completed"
    event.input_tokens = input_tokens
    event.output_tokens = output_tokens
    event.completed_at = datetime.now(timezone.utc)
    db.commit()


def release_ai_call(db: Session, event_id, *, error_code: str) -> None:
    """Refund a pre-reserved call if no provider response was produced."""
    event = db.scalar(select(AiUsageEvent).where(AiUsageEvent.id == event_id).with_for_update())
    if event is None or event.status != "reserved":
        return
    quota = ensure_user_quota(db, event.user_id, lock=True)
    user_usage = _user_daily_usage(db, event.user_id, event.usage_date, lock=True)
    project_usage = _project_daily_usage(db, event.usage_date, lock=True)
    quota.credit_balance += 1
    user_usage.calls_used = max(0, user_usage.calls_used - 1)
    project_usage.calls_used = max(0, project_usage.calls_used - 1)
    event.status = "failed"
    event.error_code = error_code[:80]
    event.completed_at = datetime.now(timezone.utc)
    db.commit()


def update_user_quota(
    db: Session,
    *,
    user_id,
    daily_limit: int | None = None,
    credit_balance: int | None = None,
    daily_used: int | None = None,
    plan_code: str | None = None,
) -> QuotaSnapshot:
    """Admin-only changes. Project capacity remains immutable outside environment config."""
    usage_date = current_usage_date()
    quota = ensure_user_quota(db, user_id, lock=True)
    user_usage = _user_daily_usage(db, user_id, usage_date, lock=True)
    project_usage = _project_daily_usage(db, usage_date, lock=True)
    settings = get_settings()
    if daily_limit is not None:
        quota.daily_limit = daily_limit
    if credit_balance is not None:
        quota.credit_balance = credit_balance
    if plan_code is not None:
        quota.plan_code = plan_code
    if daily_used is not None:
        delta = daily_used - user_usage.calls_used
        if project_usage.calls_used + delta > settings.ai_daily_project_limit:
            raise AiQuotaExceededError("project_daily_limit_reached")
        user_usage.calls_used = daily_used
        project_usage.calls_used = max(0, project_usage.calls_used + delta)
    db.commit()
    return quota_snapshot(db, user_id)
