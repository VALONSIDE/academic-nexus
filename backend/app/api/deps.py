import uuid
from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.pre_registration import PreRegistration
from app.models.user import User
from app.services.admin_scope import ADMINISTRATOR_ROLES, SUPER_ADMIN_ROLES

bearer_scheme = HTTPBearer(auto_error=False)
DbSession = Annotated[Session, Depends(get_db)]


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: DbSession,
) -> User:
    """Resolve a signed JWT into an active user / 将已签名 JWT 解析为有效用户。"""
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required or token expired / 请登录或令牌已过期",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized
    payload = decode_access_token(credentials.credentials)
    if payload is None or payload.get("scope") != "authenticated" or not payload.get("sub"):
        raise unauthorized
    try:
        user_id = uuid.UUID(payload["sub"])
    except (ValueError, TypeError):
        raise unauthorized from None
    user = db.scalar(select(User).options(selectinload(User.roles)).where(User.id == user_id))
    if user is None or not user.is_active or payload.get("auth_version") != user.auth_version:
        raise unauthorized
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_pending_registration_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: DbSession,
) -> User:
    """Allow a temporary token to submit the mandatory academic portrait only."""
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Profile-completion session is invalid or expired / 学术画像填写会话无效或已过期",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized
    payload = decode_access_token(credentials.credentials)
    if payload is None or payload.get("scope") != "profile_completion" or not payload.get("sub"):
        raise unauthorized
    try:
        user_id = uuid.UUID(payload["sub"])
    except (ValueError, TypeError):
        raise unauthorized from None
    user = db.scalar(
        select(User)
        .options(selectinload(User.roles), selectinload(User.student_profile), selectinload(User.mentor_profile))
        .where(User.id == user_id)
    )
    if (
        user is None
        or user.is_active
        or user.pre_registration_id is None
        or payload.get("auth_version") != user.auth_version
    ):
        raise unauthorized
    pre_registration = db.scalar(select(PreRegistration).where(PreRegistration.id == user.pre_registration_id).with_for_update().execution_options(populate_existing=True))
    if pre_registration is None or pre_registration.status != "issued":
        raise unauthorized
    # Activation restarts use the same receipt lock; recheck the token after
    # acquiring it so a request cannot finish with a superseded password/session.
    db.refresh(user)
    if user.is_active or payload.get("auth_version") != user.auth_version:
        raise unauthorized
    return user


PendingRegistrationUser = Annotated[User, Depends(get_pending_registration_user)]


def require_roles(*allowed_roles: str) -> Callable:
    """RBAC dependency factory / RBAC 依赖工厂。"""

    def role_checker(current_user: CurrentUser) -> User:
        current_roles = {role.code for role in current_user.roles}
        if not current_roles.intersection(allowed_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permission / 权限不足",
            )
        return current_user

    return role_checker


def require_administrator(current_user: CurrentUser) -> User:
    """Allow either a scoped institution administrator or a super administrator."""
    current_roles = {role.code for role in current_user.roles}
    if not current_roles.intersection(ADMINISTRATOR_ROLES):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator permission required / 需要管理员权限")
    return current_user


def require_super_admin(current_user: CurrentUser) -> User:
    """Allow the new role and the legacy ``admin`` bootstrap role."""
    current_roles = {role.code for role in current_user.roles}
    if not current_roles.intersection(SUPER_ADMIN_ROLES):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Super administrator permission required / 需要超级管理员权限")
    return current_user
