"""Public and management schemas for courses, papers, and books."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


ResourceType = Literal["course", "paper", "book"]


class ResourceResponse(BaseModel):
    id: UUID
    resource_type: ResourceType
    title: str
    description: str
    topics: list[str]
    tags: list[str]
    external_url: str | None
    file_original_name: str | None
    file_size_bytes: int
    download_url: str | None
    owner_name: str
    created_at: datetime
    metadata: dict[str, str | int | None] = Field(default_factory=dict)
    recommendation_score: int | None = Field(default=None, ge=0, le=100)


class ResourceListResponse(BaseModel):
    ranking_mode: Literal["local", "semantic", "hybrid"] | None = None
    items: list[ResourceResponse]
    total: int


class MentorResourceQuotaResponse(BaseModel):
    quota_bytes: int
    used_bytes: int
    remaining_bytes: int


class AdminResourceQuotaUserResponse(MentorResourceQuotaResponse):
    user_id: UUID
    username: str
    full_name: str


class AdminResourceQuotaListResponse(BaseModel):
    items: list[AdminResourceQuotaUserResponse]
    total: int


class AdminResourceQuotaUpdateRequest(BaseModel):
    quota_mb: int = Field(ge=1, le=2048)

    @field_validator("quota_mb")
    @classmethod
    def keep_valid_quota(cls, quota_mb: int) -> int:
        return quota_mb
