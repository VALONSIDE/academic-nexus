"""Request and response schemas for the MiniMax-backed assistant."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


AiTopic = Literal["academic_planning", "mentor_consultation", "learning_roadmap", "selection_advisor"]


class AiConversationCreateRequest(BaseModel):
    topic: AiTopic
    title: str | None = Field(default=None, max_length=160)

    @field_validator("title")
    @classmethod
    def normalize_title(cls, title: str | None) -> str | None:
        return title.strip() or None if title is not None else None


class AiMessageCreateRequest(BaseModel):
    content: str = Field(min_length=1, max_length=6000)

    @field_validator("content")
    @classmethod
    def normalize_content(cls, content: str) -> str:
        normalized = content.strip()
        if not normalized:
            raise ValueError("Message cannot be empty / 消息不能为空")
        return normalized


class AiMessageResponse(BaseModel):
    id: UUID
    role: Literal["user", "assistant"]
    content: str
    created_at: datetime


class AiConversationResponse(BaseModel):
    id: UUID
    topic: AiTopic
    title: str
    last_message_at: datetime | None
    created_at: datetime


class AiConversationDetailResponse(AiConversationResponse):
    messages: list[AiMessageResponse]


class AiQuotaResponse(BaseModel):
    plan_code: str
    daily_limit: int
    daily_used: int
    daily_remaining: int
    credit_balance: int
    project_daily_limit: int
    project_daily_used: int
    project_daily_remaining: int


class AiChatResponse(BaseModel):
    user_message: AiMessageResponse
    assistant_message: AiMessageResponse
    quota: AiQuotaResponse


class AdminAiQuotaUserResponse(BaseModel):
    user_id: UUID
    username: str
    full_name: str
    role: Literal["student", "mentor"]
    plan_code: str
    daily_limit: int
    daily_used: int
    credit_balance: int


class AdminAiQuotaListResponse(BaseModel):
    items: list[AdminAiQuotaUserResponse]
    total: int
    project_daily_limit: int
    project_daily_used: int
    project_daily_remaining: int


class AdminAiQuotaUpdateRequest(BaseModel):
    daily_limit: int | None = Field(default=None, ge=1, le=500)
    credit_balance: int | None = Field(default=None, ge=0, le=100000)
    daily_used: int | None = Field(default=None, ge=0, le=500)
    plan_code: str | None = Field(default=None, min_length=2, max_length=32)

    @field_validator("plan_code")
    @classmethod
    def normalize_plan(cls, plan_code: str | None) -> str | None:
        return plan_code.strip().lower() if plan_code is not None else None
