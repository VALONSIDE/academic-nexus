from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.orm import selectinload

from app.api.deps import DbSession, require_administrator
from app.api.v1.endpoints.auth import serialize_user
from app.api.v1.endpoints.profiles import (
    _mentor_data,
    _student_data,
    apply_mentor_profile,
    apply_student_profile,
)
from app.core.security import hash_password
from app.models.user import MentorProfile, StudentProfile, User
from app.services.admin_scope import can_manage_user, institution_admin_abbrs, is_super_admin
from app.schemas.profiles import (
    AdminUserBatchUpdateRequest,
    AdminUserBatchUpdateResponse,
    AdminPasswordResetRequest,
    AdminUserUpdateRequest,
    ManagedUserListResponse,
    ManagedUserResponse,
)

router = APIRouter(prefix="/admin/users", tags=["User administration / 用户管理"])
ManagedRole = Literal["student", "mentor"]


def _managed_role(user: User) -> ManagedRole | None:
    if any(role.code == "student" for role in user.roles):
        return "student"
    if any(role.code == "mentor" for role in user.roles):
        return "mentor"
    return None


def serialize_managed_user(user: User) -> ManagedUserResponse:
    role = _managed_role(user)
    if role == "student" and user.student_profile is not None:
        profile = user.student_profile
        return ManagedUserResponse(
            **serialize_user(user).model_dump(),
            role=role,
            phone=user.phone,
            academic_id=profile.student_no,
            institution_abbr=profile.institution_abbr,
            institution_name_zh=profile.university,
            college_name_zh=profile.department,
            profile_completed=profile.profile_completed_at is not None,
            profile=_student_data(profile),
        )
    if role == "mentor" and user.mentor_profile is not None:
        profile = user.mentor_profile
        return ManagedUserResponse(
            **serialize_user(user).model_dump(),
            role=role,
            phone=user.phone,
            academic_id=profile.employee_no,
            institution_abbr=profile.institution_abbr,
            institution_name_zh=profile.university,
            college_name_zh=profile.department,
            profile_completed=profile.profile_completed_at is not None,
            profile=_mentor_data(profile),
        )
    raise ValueError("Only students and mentors can be managed here")


def _load_managed_user(db: DbSession, admin: User, user_id: UUID) -> User:
    user = db.scalar(
        select(User)
        .options(selectinload(User.roles), selectinload(User.student_profile), selectinload(User.mentor_profile))
        .where(User.id == user_id, User.tenant_id == admin.tenant_id)
    )
    if user is None or _managed_role(user) is None or not can_manage_user(db, admin, user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found / 未找到用户")
    return user


@router.get("", response_model=ManagedUserListResponse, summary="List students or mentors / 查询学生或导师")
def list_managed_users(
    db: DbSession,
    admin: User = Depends(require_administrator),
    role: ManagedRole = Query(...),
    search: str = Query(default="", max_length=100),
) -> ManagedUserListResponse:
    statement = (
        select(User)
        .options(selectinload(User.roles), selectinload(User.student_profile), selectinload(User.mentor_profile))
        .join(User.roles)
        .where(User.tenant_id == admin.tenant_id)
        .where(User.roles.any(code=role))
        .order_by(User.created_at.desc())
    )
    if not is_super_admin(admin):
        scopes = institution_admin_abbrs(db, admin)
        if role == "student":
            statement = statement.where(User.student_profile.has(StudentProfile.institution_abbr.in_(scopes)))
        else:
            statement = statement.where(User.mentor_profile.has(MentorProfile.institution_abbr.in_(scopes)))
    normalized_search = search.strip()
    if normalized_search:
        pattern = f"%{normalized_search}%"
        statement = statement.where(or_(User.username.ilike(pattern), User.full_name.ilike(pattern)))
    users = db.scalars(statement).unique().all()
    managed = [serialize_managed_user(user) for user in users if _managed_role(user) == role]
    return ManagedUserListResponse(items=managed, total=len(managed))


@router.patch("/{user_id}", response_model=ManagedUserResponse, summary="Update a student or mentor / 更新学生或导师资料")
def update_managed_user(
    user_id: UUID,
    payload: AdminUserUpdateRequest,
    db: DbSession,
    admin: User = Depends(require_administrator),
) -> ManagedUserResponse:
    user = _load_managed_user(db, admin, user_id)
    role = _managed_role(user)
    if payload.full_name is not None:
        user.full_name = payload.full_name
    if payload.phone is not None:
        user.phone = payload.phone or None
    if payload.preferred_locale is not None:
        user.preferred_locale = payload.preferred_locale
    if payload.is_active is not None:
        if user.is_active and not payload.is_active:
            user.auth_version += 1
        user.is_active = payload.is_active
    if payload.student_profile is not None:
        if role != "student" or user.student_profile is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Student profile does not match this user / 学生画像与该用户不匹配")
        apply_student_profile(user.student_profile, payload.student_profile)
    if payload.mentor_profile is not None:
        if role != "mentor" or user.mentor_profile is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Mentor profile does not match this user / 导师画像与该用户不匹配")
        apply_mentor_profile(user.mentor_profile, payload.mentor_profile)
    db.commit()
    db.refresh(user)
    return serialize_managed_user(user)


@router.post("/batch-status", response_model=AdminUserBatchUpdateResponse, summary="Batch enable or disable users / 批量启用或停用用户")
def batch_update_user_status(
    payload: AdminUserBatchUpdateRequest,
    db: DbSession,
    admin: User = Depends(require_administrator),
) -> AdminUserBatchUpdateResponse:
    user_ids = list(set(payload.user_ids))
    users = db.scalars(
        select(User)
        .options(selectinload(User.roles), selectinload(User.student_profile), selectinload(User.mentor_profile))
        .where(User.id.in_(user_ids), User.tenant_id == admin.tenant_id)
        .with_for_update()
    ).all()
    managed = [user for user in users if _managed_role(user) is not None and can_manage_user(db, admin, user)]
    if len(managed) != len(user_ids):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "user_not_found"})
    for user in managed:
        if user.is_active and not payload.is_active:
            user.auth_version += 1
        user.is_active = payload.is_active
    db.commit()
    return AdminUserBatchUpdateResponse(updated=len(managed))


@router.post("/{user_id}/password", status_code=status.HTTP_204_NO_CONTENT, summary="Reset a user password / 重置用户密码")
def reset_managed_user_password(
    user_id: UUID,
    payload: AdminPasswordResetRequest,
    db: DbSession,
    admin: User = Depends(require_administrator),
) -> None:
    user = _load_managed_user(db, admin, user_id)
    user.password_hash = hash_password(payload.new_password)
    user.auth_version += 1
    db.commit()
