"""Dashboard metrics derived from real platform state, not placeholder copy."""

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DbSession
from app.models.ai import AiProjectDailyUsage
from app.models.pre_registration import PreRegistration
from app.models.resource import Resource
from app.models.selection import MentorSelection
from app.models.user import User
from app.schemas.dashboard import DashboardBreakdown, DashboardMetric, DashboardResponse, DashboardSelectionActivity
from app.services.ai.quota import current_usage_date, quota_snapshot as ai_quota_snapshot
from app.services.resources import quota_snapshot as resource_quota_snapshot

from fastapi import APIRouter


router = APIRouter(prefix="/dashboard", tags=["Dashboard / 概览"])


def _count(db: DbSession, statement) -> int:
    return int(db.scalar(statement) or 0)


def _role(user: User) -> str:
    if any(role.code == "admin" for role in user.roles):
        return "admin"
    if any(role.code == "mentor" for role in user.roles):
        return "mentor"
    return "student"


def _selection_data(db: DbSession, user: User, role: str) -> tuple[list[DashboardBreakdown], list[DashboardSelectionActivity]]:
    statement = select(MentorSelection).where(MentorSelection.tenant_id == user.tenant_id)
    if role == "student": statement = statement.where(MentorSelection.student_user_id == user.id)
    if role == "mentor": statement = statement.where(MentorSelection.mentor_user_id == user.id)
    rows = db.scalars(statement.order_by(MentorSelection.updated_at.desc())).all()
    counts = {code: 0 for code in ("pending_student", "pending_mentor", "confirmed", "rejected", "cancelled")}
    for row in rows: counts[row.status] = counts.get(row.status, 0) + 1
    user_ids = {item.student_user_id for item in rows[:8]} | {item.mentor_user_id for item in rows[:8]}
    names = {item.id: item.full_name for item in db.scalars(select(User).where(User.id.in_(user_ids))).all()} if user_ids else {}
    activity = [DashboardSelectionActivity(id=str(item.id), student_name=names.get(item.student_user_id, ""), mentor_name=names.get(item.mentor_user_id, ""), status=item.status, updated_at=item.updated_at) for item in rows[:8]]
    return [DashboardBreakdown(code=code, value=value) for code, value in counts.items()], activity


@router.get("", response_model=DashboardResponse, summary="Read workspace dashboard / 获取工作台概览")
def read_dashboard(current_user: CurrentUser, db: DbSession) -> DashboardResponse:
    role = _role(current_user)
    resource_rows = db.execute(
        select(Resource.resource_type, func.count(Resource.id))
        .where(Resource.tenant_id == current_user.tenant_id, Resource.is_published.is_(True))
        .group_by(Resource.resource_type)
    ).all()
    distribution = [DashboardBreakdown(code=resource_type, value=count) for resource_type, count in resource_rows]
    selection_statistics, recent_activity = _selection_data(db, current_user, role)
    if role == "admin":
        student_total = _count(db, select(func.count(User.id)).where(User.tenant_id == current_user.tenant_id, User.roles.any(code="student")))
        mentor_total = _count(db, select(func.count(User.id)).where(User.tenant_id == current_user.tenant_id, User.roles.any(code="mentor")))
        preregistered = _count(db, select(func.count(PreRegistration.id)).where(PreRegistration.tenant_id == current_user.tenant_id, PreRegistration.status == "issued"))
        project_used = _count(db, select(AiProjectDailyUsage.calls_used).where(AiProjectDailyUsage.usage_date == current_usage_date()))
        from app.core.config import get_settings
        return DashboardResponse(
            role="admin",
            metrics=[
                DashboardMetric(code="students_total", value=student_total),
                DashboardMetric(code="mentors_total", value=mentor_total),
                DashboardMetric(code="preregistrations_pending", value=preregistered),
                DashboardMetric(code="resources_total", value=sum(item.value for item in distribution)),
                DashboardMetric(code="ai_project_calls", value=project_used, total=get_settings().ai_daily_project_limit),
            ],
            profile_completion=[],
            resource_distribution=distribution,
            selection_statistics=selection_statistics,
            recent_selection_activity=recent_activity,
        )
    if role == "student":
        student = db.scalar(select(User).options(selectinload(User.student_profile)).where(User.id == current_user.id))
        ai_quota = ai_quota_snapshot(db, current_user.id)
        mentors = _count(db, select(func.count(User.id)).where(User.tenant_id == current_user.tenant_id, User.is_active.is_(True), User.roles.any(code="mentor")))
        db.commit()
        return DashboardResponse(
            role="student",
            metrics=[
                DashboardMetric(code="mentor_matches_available", value=mentors),
                DashboardMetric(code="resources_total", value=sum(item.value for item in distribution)),
                DashboardMetric(code="ai_daily_calls", value=ai_quota.daily_used, total=ai_quota.daily_limit),
                DashboardMetric(code="ai_credit_balance", value=ai_quota.credit_balance),
            ],
            profile_completion=[],
            resource_distribution=distribution,
            selection_statistics=selection_statistics,
            recent_selection_activity=recent_activity,
        )
    mentor = db.scalar(select(User).options(selectinload(User.mentor_profile)).where(User.id == current_user.id))
    ai_quota = ai_quota_snapshot(db, current_user.id)
    resource_quota = resource_quota_snapshot(db, current_user.id)
    candidates = _count(db, select(func.count(User.id)).where(User.tenant_id == current_user.tenant_id, User.is_active.is_(True), User.roles.any(code="student")))
    own_resources = _count(db, select(func.count(Resource.id)).where(Resource.tenant_id == current_user.tenant_id, Resource.owner_user_id == current_user.id))
    db.commit()
    return DashboardResponse(
        role="mentor",
        metrics=[
            DashboardMetric(code="student_candidates_available", value=candidates),
            DashboardMetric(code="resources_owned", value=own_resources),
            DashboardMetric(code="resource_storage", value=resource_quota.used_bytes, total=resource_quota.quota_bytes),
            DashboardMetric(code="ai_daily_calls", value=ai_quota.daily_used, total=ai_quota.daily_limit),
        ],
        profile_completion=[],
        resource_distribution=distribution,
        selection_statistics=selection_statistics,
        recent_selection_activity=recent_activity,
    )
