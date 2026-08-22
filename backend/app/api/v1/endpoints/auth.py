from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DbSession
from app.core.security import create_access_token, hash_password, verify_password
from app.models.pre_registration import PreRegistration
from app.models.user import MentorProfile, Role, StudentProfile, User
from app.schemas.auth import (
    ActivationRequest,
    ActivationStartResponse,
    AuthResponse,
    LocaleUpdateRequest,
    LoginRequest,
    PasswordChangeRequest,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["Authentication / 身份认证"])


def profile_is_complete(user: User) -> bool:
    if any(role.code == "student" for role in user.roles):
        return bool(user.student_profile and user.student_profile.profile_completed_at)
    if any(role.code == "mentor" for role in user.roles):
        return bool(user.mentor_profile and user.mentor_profile.profile_completed_at)
    return True


def serialize_user(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        username=user.username or "",
        full_name=user.full_name,
        preferred_locale=user.preferred_locale,
        is_active=user.is_active,
        roles=sorted(role.code for role in user.roles),
    )


def authenticate_response(user: User) -> AuthResponse:
    roles = sorted(role.code for role in user.roles)
    return AuthResponse(
        access_token=create_access_token(subject=str(user.id), roles=roles),
        user=serialize_user(user),
    )


def _invalid_activation() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Activation details are invalid or the Access Key has expired / 激活信息错误或 Access Key 已失效",
    )


@router.post(
    "/activate",
    response_model=ActivationStartResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start pre-registered account activation / 开始预注册账户激活",
)
def start_activation(payload: ActivationRequest, db: DbSession) -> ActivationStartResponse:
    """Verify the four receipt fields, then issue a short-lived profile-completion token.

    The user remains unable to log in until the mandatory Phase 2 portrait is saved.
    A participant can safely restart this step with their receipt while the key is still issued.
    """
    invalid_activation = _invalid_activation()
    pre_registration = db.scalar(
        select(PreRegistration)
        .where(PreRegistration.username == payload.username)
        .with_for_update()
    )
    if (
        pre_registration is None
        or pre_registration.status != "issued"
        or pre_registration.full_name != payload.full_name.strip()
        or pre_registration.academic_id != payload.academic_id
        or not verify_password(payload.access_key, pre_registration.access_key_hash)
    ):
        raise invalid_activation

    role = db.scalar(
        select(Role).where(Role.tenant_id == pre_registration.tenant_id, Role.code == pre_registration.role_code)
    )
    if role is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Activation role is unavailable / 激活角色暂不可用",
        )

    user = db.scalar(
        select(User)
        .options(selectinload(User.roles), selectinload(User.student_profile), selectinload(User.mentor_profile))
        .where(User.pre_registration_id == pre_registration.id)
        .with_for_update()
    )
    if user is not None and user.is_active:
        raise invalid_activation
    if user is None:
        user = User(
            tenant_id=pre_registration.tenant_id,
            username=pre_registration.username,
            pre_registration_id=pre_registration.id,
            full_name=pre_registration.full_name,
            password_hash=hash_password(payload.password),
            preferred_locale=payload.preferred_locale,
            is_active=False,
            is_verified=False,
        )
        user.roles.append(role)
        db.add(user)
        db.flush()
    else:
        # Restarting the incomplete process requires all receipt fields and the key again.
        user.password_hash = hash_password(payload.password)
        user.preferred_locale = payload.preferred_locale

    if pre_registration.role_code == "student":
        profile = user.student_profile or db.scalar(select(StudentProfile).where(StudentProfile.user_id == user.id))
        if profile is None:
            db.add(
                StudentProfile(
                    user_id=user.id,
                    student_no=pre_registration.academic_id,
                    university=pre_registration.institution_name_zh,
                    department=pre_registration.college_name_zh,
                    institution_abbr=pre_registration.institution_abbr,
                )
            )
        else:
            profile.student_no = pre_registration.academic_id
            profile.university = pre_registration.institution_name_zh
            profile.department = pre_registration.college_name_zh
            profile.institution_abbr = pre_registration.institution_abbr
    else:
        profile = user.mentor_profile or db.scalar(select(MentorProfile).where(MentorProfile.user_id == user.id))
        if profile is None:
            db.add(
                MentorProfile(
                    user_id=user.id,
                    employee_no=pre_registration.academic_id,
                    university=pre_registration.institution_name_zh,
                    department=pre_registration.college_name_zh,
                    institution_abbr=pre_registration.institution_abbr,
                )
            )
        else:
            profile.employee_no = pre_registration.academic_id
            profile.university = pre_registration.institution_name_zh
            profile.department = pre_registration.college_name_zh
            profile.institution_abbr = pre_registration.institution_abbr

    db.commit()
    return ActivationStartResponse(
        registration_token=create_access_token(
            subject=str(user.id), roles=[pre_registration.role_code], scope="profile_completion"
        ),
        role=pre_registration.role_code,
    )


@router.post("/login", response_model=AuthResponse, summary="Log in / 登录")
def login(payload: LoginRequest, db: DbSession) -> AuthResponse:
    username = payload.username.strip().upper()
    user = db.scalar(
        select(User)
        .options(selectinload(User.roles), selectinload(User.student_profile), selectinload(User.mentor_profile))
        .where(User.username == username)
        .order_by(User.created_at)
    )
    # Do not reveal whether an account exists, is incomplete, disabled, or has a wrong password.
    if user is None or not user.is_active or not profile_is_complete(user) or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password / 用户名或密码错误",
        )
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()
    return authenticate_response(user)


@router.get("/me", response_model=UserResponse, summary="Read current user / 获取当前用户")
def read_me(current_user: CurrentUser) -> UserResponse:
    return serialize_user(current_user)


@router.patch("/me/locale", response_model=UserResponse, summary="Update language preference / 更新语言偏好")
def update_locale(payload: LocaleUpdateRequest, current_user: CurrentUser, db: DbSession) -> UserResponse:
    current_user.preferred_locale = payload.preferred_locale
    db.commit()
    db.refresh(current_user)
    return serialize_user(current_user)


@router.post("/me/password", status_code=status.HTTP_204_NO_CONTENT, summary="Change own password / 修改自己的密码")
def change_own_password(payload: PasswordChangeRequest, current_user: CurrentUser, db: DbSession) -> None:
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"code": "current_password_incorrect"})
    current_user.password_hash = hash_password(payload.new_password)
    db.commit()
