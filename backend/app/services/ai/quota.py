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
from app.services.subscriptions import SubscriptionSnapshot, refresh_subscription, subscription_snapshot


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
    cycle_started_at: datetime
    cycle_ends_at: datetime
    cycle_credit_limit: int
    cycle_credits_used: int


def current_usage_date() -> date:
    """Quota day follows the platform's primary operating timezone."""
    return datetime.now(ZoneInfo("Asia/Shanghai")).date()


def _quota(db: Session, user_id, *, lock: bool = False) -> AiUserQuota | None:
    statement = select(AiUserQuota).where(AiUserQuota.user_id == user_id)
    if lock:
        db.flush()
        statement = statement.with_for_update().execution_options(populate_existing=True)
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
        db.flush()
        statement = statement.with_for_update().execution_options(populate_existing=True)
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
        db.flush()
        statement = statement.with_for_update().execution_options(populate_existing=True)
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
    user = db.scalar(select(User).where(User.id == user_id))
    if user is None:
        raise ValueError("User not found")
    entitlement: SubscriptionSnapshot = subscription_snapshot(db, user)
    quota = _quota(db, user_id)
    if quota is None:  # Defensive: subscription_snapshot always synchronizes it.
        quota = ensure_user_quota(db, user_id)
    project_usage = _project_daily_usage(db, usage_date)
    settings = get_settings()
    # Keep the historical response fields for old clients, but their values now
    # express the active subscription cycle rather than a daily personal cap.
    daily_remaining = entitlement.credit_balance
    return QuotaSnapshot(
        plan_code=entitlement.plan_code,
        daily_limit=entitlement.credit_limit,
        daily_used=entitlement.credits_used,
        daily_remaining=daily_remaining,
        credit_balance=entitlement.credit_balance,
        project_daily_limit=settings.ai_daily_project_limit,
        project_daily_used=project_usage.calls_used,
        project_daily_remaining=max(0, settings.ai_daily_project_limit - project_usage.calls_used),
        cycle_started_at=entitlement.cycle_started_at,
        cycle_ends_at=entitlement.cycle_ends_at,
        cycle_credit_limit=entitlement.credit_limit,
        cycle_credits_used=entitlement.credits_used,
    )


def reserve_ai_call(
    db: Session,
    user: User,
    conversation_id,
    *,
    model: str | None = None,
    credit_cost: int = 1,
) -> AiUsageEvent:
    """Reserve the selected model's credit cost before reaching the provider.

    The rows are locked in a stable order, so concurrent requests cannot exceed the
    subscription-cycle balance or the project-wide environment-controlled ceiling.
    """
    usage_date = current_usage_date()
    if credit_cost < 1:
        raise ValueError("credit_cost must be positive")
    refresh_subscription(db, user, lock=True)
    quota = _quota(db, user.id, lock=True)
    if quota is None:
        quota = ensure_user_quota(db, user.id, lock=True)
    user_usage = _user_daily_usage(db, user.id, usage_date, lock=True)
    project_usage = _project_daily_usage(db, usage_date, lock=True)
    settings = get_settings()
    if quota.credit_balance < credit_cost:
        raise AiQuotaExceededError("credit_balance_exhausted")
    if project_usage.calls_used + credit_cost > settings.ai_daily_project_limit:
        raise AiQuotaExceededError("project_daily_limit_reached")

    user_usage.calls_used += credit_cost
    project_usage.calls_used += credit_cost
    quota.credit_balance -= credit_cost
    event = AiUsageEvent(
        tenant_id=user.tenant_id,
        user_id=user.id,
        conversation_id=conversation_id,
        usage_date=usage_date,
        model=model or settings.minimax_model,
        credit_cost=credit_cost,
        status="reserved",
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def complete_ai_call(db: Session, event_id, *, input_tokens: int | None, output_tokens: int | None, commit: bool = True) -> None:
    event = db.scalar(select(AiUsageEvent).where(AiUsageEvent.id == event_id).with_for_update().execution_options(populate_existing=True))
    if event is None or event.status != "reserved":
        return
    event.status = "completed"
    event.input_tokens = input_tokens
    event.output_tokens = output_tokens
    event.completed_at = datetime.now(timezone.utc)
    if commit:
        db.commit()


def release_ai_call(db: Session, event_id, *, error_code: str) -> None:
    """Refund a pre-reserved call if no provider response was produced."""
    event = db.scalar(select(AiUsageEvent).where(AiUsageEvent.id == event_id).with_for_update().execution_options(populate_existing=True))
    if event is None or event.status != "reserved":
        return
    user = db.get(User, event.user_id)
    if user is None:
        return
    subscription = refresh_subscription(db, user, lock=True)
    quota = _quota(db, event.user_id, lock=True)
    if quota is None:
        quota = ensure_user_quota(db, event.user_id, lock=True)
    user_usage = _user_daily_usage(db, event.user_id, event.usage_date, lock=True)
    project_usage = _project_daily_usage(db, event.usage_date, lock=True)
    event_time = event.created_at.replace(tzinfo=timezone.utc) if event.created_at.tzinfo is None else event.created_at
    cycle_start = subscription.cycle_started_at.replace(tzinfo=timezone.utc) if subscription.cycle_started_at.tzinfo is None else subscription.cycle_started_at
    if event_time >= cycle_start:
        quota.credit_balance = min(subscription.credit_limit, quota.credit_balance + event.credit_cost)
    user_usage.calls_used = max(0, user_usage.calls_used - event.credit_cost)
    project_usage.calls_used = max(0, project_usage.calls_used - event.credit_cost)
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
    user = db.scalar(select(User).where(User.id == user_id))
    if user is None:
        raise ValueError("User not found")
    subscription = refresh_subscription(db, user, lock=True)
    quota = _quota(db, user_id, lock=True)
    if quota is None:
        quota = ensure_user_quota(db, user_id, lock=True)
    user_usage = _user_daily_usage(db, user_id, usage_date, lock=True)
    project_usage = _project_daily_usage(db, usage_date, lock=True)
    settings = get_settings()
    if daily_limit is not None:
        quota.daily_limit = daily_limit
        subscription.credit_limit = daily_limit
    if credit_balance is not None:
        quota.credit_balance = credit_balance
    if plan_code is not None:
        quota.plan_code = plan_code
        subscription.plan_code = plan_code
    if daily_used is not None:
        delta = daily_used - user_usage.calls_used
        if project_usage.calls_used + delta > settings.ai_daily_project_limit:
            raise AiQuotaExceededError("project_daily_limit_reached")
        user_usage.calls_used = daily_used
        project_usage.calls_used = max(0, project_usage.calls_used + delta)
    db.commit()
    return quota_snapshot(db, user_id)
