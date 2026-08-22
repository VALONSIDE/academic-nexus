"""Phase 2 academic-portrait request and response schemas."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.schemas.auth import Locale, UserResponse, validate_password_strength


def _normalize_tags(values: list[str]) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = value.strip()
        key = normalized.casefold()
        if normalized and key not in seen:
            cleaned.append(normalized)
            seen.add(key)
    if not 1 <= len(cleaned) <= 12:
        raise ValueError("Provide 1-12 distinct entries / 请填写 1-12 个不重复条目")
    if any(len(item) > 100 for item in cleaned):
        raise ValueError("Each entry must be 100 characters or fewer / 单项不得超过 100 个字符")
    return cleaned


class StudentAcademicProfilePayload(BaseModel):
    research_interests: list[str] = Field(min_length=1, max_length=12)
    skills: list[str] = Field(min_length=1, max_length=12)
    academic_performance: str = Field(min_length=2, max_length=3000)
    academic_goals: str = Field(min_length=2, max_length=3000)
    research_experience: str = Field(min_length=2, max_length=5000)

    @field_validator("research_interests", "skills")
    @classmethod
    def normalize_tags(cls, values: list[str]) -> list[str]:
        return _normalize_tags(values)

    @field_validator("academic_performance", "academic_goals", "research_experience")
    @classmethod
    def trim_text(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) < 2:
            raise ValueError("This field is required / 此项为必填")
        return normalized


class MentorAcademicProfilePayload(BaseModel):
    research_directions: list[str] = Field(min_length=1, max_length=12)
    representative_papers: list[str] = Field(min_length=1, max_length=12)
    research_projects: str = Field(min_length=2, max_length=5000)
    mentoring_style: str = Field(min_length=2, max_length=3000)

    @field_validator("research_directions", "representative_papers")
    @classmethod
    def normalize_tags(cls, values: list[str]) -> list[str]:
        return _normalize_tags(values)

    @field_validator("research_projects", "mentoring_style")
    @classmethod
    def trim_text(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) < 2:
            raise ValueError("This field is required / 此项为必填")
        return normalized


class AcademicProfileResponse(BaseModel):
    role: str
    profile_completed: bool
    completed_at: datetime | None = None
    data: dict[str, Any]


class ManagedUserResponse(UserResponse):
    phone: str | None = None
    role: str
    academic_id: str | None = None
    institution_abbr: str | None = None
    institution_name_zh: str | None = None
    college_name_zh: str | None = None
    profile_completed: bool
    profile: dict[str, Any]


class AdminUserUpdateRequest(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    phone: str | None = Field(default=None, max_length=32)
    preferred_locale: Locale | None = None
    is_active: bool | None = None
    student_profile: StudentAcademicProfilePayload | None = None
    mentor_profile: MentorAcademicProfilePayload | None = None

    @field_validator("full_name", "phone")
    @classmethod
    def trim_optional_text(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None


class AdminUserBatchUpdateRequest(BaseModel):
    user_ids: list[UUID] = Field(min_length=1, max_length=500)
    is_active: bool


class AdminUserBatchUpdateResponse(BaseModel):
    updated: int


class AdminPasswordResetRequest(BaseModel):
    new_password: str = Field(min_length=12, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, password: str) -> str:
        return validate_password_strength(password)


class ManagedUserListResponse(BaseModel):
    items: list[ManagedUserResponse]
    total: int
