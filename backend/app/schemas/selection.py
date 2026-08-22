from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


SelectionStatus = Literal["pending_student", "pending_mentor", "confirmed", "rejected", "cancelled"]
SelectionMode = Literal["manual", "first_come"]


class NotePayload(BaseModel):
    note: str | None = Field(default=None, max_length=2000)


class SelectionResponse(BaseModel):
    id: UUID
    student_user_id: UUID
    mentor_user_id: UUID
    status: SelectionStatus
    student_note: str | None
    mentor_note: str | None
    created_at: datetime
    updated_at: datetime
    confirmed_at: datetime | None


class SelectionSettingsResponse(BaseModel):
    is_open: bool
    default_capacity: int = Field(ge=1, le=200)
    default_student_choice_limit: int = Field(ge=1, le=50)


class SelectionSettingsUpdate(BaseModel):
    is_open: bool | None = None
    default_capacity: int | None = Field(default=None, ge=1, le=200)
    default_student_choice_limit: int | None = Field(default=None, ge=1, le=50)


class MentorSelectionSettingsResponse(BaseModel):
    capacity: int
    is_exempt: bool
    selection_mode: SelectionMode
    confirmed_count: int
    invitation_count: int
    available_slots: int


class MentorSelectionSettingsUpdate(BaseModel):
    capacity: int | None = Field(default=None, ge=1, le=200)
    selection_mode: SelectionMode | None = None


class AdminSelectionUserResponse(BaseModel):
    user_id: UUID
    username: str
    full_name: str
    role: Literal["student", "mentor"]
    institution_name_zh: str | None = None
    college_name_zh: str | None = None
    choice_limit: int | None = None
    capacity: int | None = None
    is_exempt: bool
    selection_mode: SelectionMode | None = None


class AdminSelectionUserUpdate(BaseModel):
    choice_limit: int | None = Field(default=None, ge=1, le=50)
    capacity: int | None = Field(default=None, ge=1, le=200)
    is_exempt: bool | None = None
    selection_mode: SelectionMode | None = None
    # An explicit flag is required because an omitted optional integer and a
    # request to clear an existing override would otherwise both be `None`.
    use_default: bool = False


class AdminSelectionRecordResponse(BaseModel):
    id: UUID
    status: SelectionStatus
    student_user_id: UUID
    student_name: str
    student_username: str
    student_institution_name_zh: str | None = None
    student_college_name_zh: str | None = None
    mentor_user_id: UUID
    mentor_name: str
    mentor_username: str
    mentor_institution_name_zh: str | None = None
    mentor_college_name_zh: str | None = None
    created_at: datetime
    updated_at: datetime
    confirmed_at: datetime | None


class AdminSelectionRecordListResponse(BaseModel):
    items: list[AdminSelectionRecordResponse]
    total: int


class AdminSelectionBulkReleaseRequest(BaseModel):
    selection_ids: list[UUID] = Field(min_length=1, max_length=500)


class SelectionCandidate(BaseModel):
    selection: SelectionResponse
    full_name: str
    username: str
    university: str | None
    department: str | None
    major: str | None
    research_interests: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    match_score: int = Field(ge=0, le=100)


class SelectionCandidateListResponse(BaseModel):
    settings: MentorSelectionSettingsResponse
    items: list[SelectionCandidate]
