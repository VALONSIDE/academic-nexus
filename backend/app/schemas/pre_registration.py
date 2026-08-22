"""Administrative read and mutation models for imported accounts."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class PreRegistrationAdminResponse(BaseModel):
    id: UUID
    batch_id: UUID
    username: str
    role_code: Literal["student", "mentor"]
    full_name: str
    academic_id: str
    institution_abbr: str
    institution_name_zh: str
    college_name_zh: str
    status: Literal["issued", "activated", "revoked"]
    created_at: datetime
    activated_at: datetime | None


class PreRegistrationListResponse(BaseModel):
    items: list[PreRegistrationAdminResponse]
    total: int


class PreRegistrationBulkDeleteRequest(BaseModel):
    ids: list[UUID] = Field(min_length=1, max_length=500)
