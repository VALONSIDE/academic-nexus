from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession, PendingRegistrationUser
from app.api.v1.endpoints.auth import authenticate_response, ensure_email_available
from app.models.pre_registration import PreRegistration
from app.models.user import MentorProfile, StudentProfile, User
from app.schemas.auth import AuthResponse
from app.schemas.profiles import (
    AcademicProfileResponse,
    MentorAcademicProfilePayload,
    MentorRegistrationCompleteRequest,
    StudentAcademicProfilePayload,
    StudentRegistrationCompleteRequest,
)

router = APIRouter(prefix="/profiles", tags=["Academic portraits / 学术画像"])


def _has_role(user: User, role: str) -> bool:
    return any(item.code == role for item in user.roles)


def _student_data(profile: StudentProfile) -> dict[str, object]:
    return {
        "research_interests": profile.research_interests or [],
        "skills": profile.skills or [],
        "academic_performance": profile.academic_performance or "",
        "academic_goals": profile.academic_goals or "",
        "research_experience": profile.research_experience or "",
    }


def _mentor_data(profile: MentorProfile) -> dict[str, object]:
    return {
        "research_directions": profile.research_directions or [],
        "representative_papers": profile.representative_papers or [],
        "research_projects": profile.research_projects or "",
        "mentoring_style": profile.mentoring_style or "",
    }


def student_profile_response(profile: StudentProfile) -> AcademicProfileResponse:
    return AcademicProfileResponse(
        role="student",
        profile_completed=profile.profile_completed_at is not None,
        completed_at=profile.profile_completed_at,
        data=_student_data(profile),
    )


def mentor_profile_response(profile: MentorProfile) -> AcademicProfileResponse:
    return AcademicProfileResponse(
        role="mentor",
        profile_completed=profile.profile_completed_at is not None,
        completed_at=profile.profile_completed_at,
        data=_mentor_data(profile),
    )


def apply_student_profile(profile: StudentProfile, payload: StudentAcademicProfilePayload, *, complete: bool = False) -> None:
    profile.research_interests = payload.research_interests
    profile.skills = payload.skills
    profile.academic_performance = payload.academic_performance
    profile.academic_goals = payload.academic_goals
    profile.research_experience = payload.research_experience
    if complete:
        profile.profile_completed_at = datetime.now(timezone.utc)


def apply_mentor_profile(profile: MentorProfile, payload: MentorAcademicProfilePayload, *, complete: bool = False) -> None:
    profile.research_directions = payload.research_directions
    profile.representative_papers = payload.representative_papers
    profile.research_projects = payload.research_projects
    profile.mentoring_style = payload.mentoring_style
    if complete:
        profile.profile_completed_at = datetime.now(timezone.utc)


@router.post(
    "/student/complete-registration",
    response_model=AuthResponse,
    summary="Complete student registration / 完成学生注册",
)
def complete_student_registration(
    payload: StudentRegistrationCompleteRequest,
    pending_user: PendingRegistrationUser,
    db: DbSession,
) -> AuthResponse:
    if not _has_role(pending_user, "student") or pending_user.student_profile is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Student profile is required / 需要学生学术画像")
    pre_registration = db.scalar(
        select(PreRegistration).where(PreRegistration.id == pending_user.pre_registration_id).with_for_update()
    )
    if pre_registration is None or pre_registration.status != "issued":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Registration has already been completed / 注册已完成")
    ensure_email_available(db, pending_user, payload.email)
    pending_user.phone = payload.phone
    pending_user.email = payload.email
    apply_student_profile(pending_user.student_profile, payload, complete=True)
    pending_user.is_active = True
    pending_user.is_verified = True
    pending_user.auth_version += 1
    pre_registration.status = "activated"
    pre_registration.activated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(pending_user)
    return authenticate_response(pending_user)


@router.post(
    "/mentor/complete-registration",
    response_model=AuthResponse,
    summary="Complete mentor registration / 完成导师注册",
)
def complete_mentor_registration(
    payload: MentorRegistrationCompleteRequest,
    pending_user: PendingRegistrationUser,
    db: DbSession,
) -> AuthResponse:
    if not _has_role(pending_user, "mentor") or pending_user.mentor_profile is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Mentor profile is required / 需要导师学术画像")
    pre_registration = db.scalar(
        select(PreRegistration).where(PreRegistration.id == pending_user.pre_registration_id).with_for_update()
    )
    if pre_registration is None or pre_registration.status != "issued":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Registration has already been completed / 注册已完成")
    ensure_email_available(db, pending_user, payload.email)
    pending_user.phone = payload.phone
    pending_user.email = payload.email
    apply_mentor_profile(pending_user.mentor_profile, payload, complete=True)
    pending_user.is_active = True
    pending_user.is_verified = True
    pending_user.auth_version += 1
    pre_registration.status = "activated"
    pre_registration.activated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(pending_user)
    return authenticate_response(pending_user)


@router.get("/student/me", response_model=AcademicProfileResponse, summary="Read student portrait / 获取学生学术画像")
def read_student_profile(current_user: CurrentUser) -> AcademicProfileResponse:
    if not _has_role(current_user, "student") or current_user.student_profile is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Student permission required / 需要学生权限")
    return student_profile_response(current_user.student_profile)


@router.put("/student/me", response_model=AcademicProfileResponse, summary="Update student portrait / 更新学生学术画像")
def update_student_profile(
    payload: StudentAcademicProfilePayload,
    db: DbSession,
    current_user: CurrentUser,
) -> AcademicProfileResponse:
    if not _has_role(current_user, "student") or current_user.student_profile is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Student permission required / 需要学生权限")
    apply_student_profile(current_user.student_profile, payload)
    db.commit()
    db.refresh(current_user.student_profile)
    return student_profile_response(current_user.student_profile)


@router.get("/mentor/me", response_model=AcademicProfileResponse, summary="Read mentor portrait / 获取导师学术画像")
def read_mentor_profile(current_user: CurrentUser) -> AcademicProfileResponse:
    if not _has_role(current_user, "mentor") or current_user.mentor_profile is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Mentor permission required / 需要导师权限")
    return mentor_profile_response(current_user.mentor_profile)


@router.put("/mentor/me", response_model=AcademicProfileResponse, summary="Update mentor portrait / 更新导师学术画像")
def update_mentor_profile(
    payload: MentorAcademicProfilePayload,
    db: DbSession,
    current_user: CurrentUser,
) -> AcademicProfileResponse:
    if not _has_role(current_user, "mentor") or current_user.mentor_profile is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Mentor permission required / 需要导师权限")
    apply_mentor_profile(current_user.mentor_profile, payload)
    db.commit()
    db.refresh(current_user.mentor_profile)
    return mentor_profile_response(current_user.mentor_profile)
