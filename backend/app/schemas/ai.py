"""Request and response schemas for the MiniMax-backed assistant."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


AiTopic = Literal["academic_planning", "mentor_consultation", "learning_roadmap", "selection_advisor"]
AiModelTier = Literal["light", "standard", "expert"]
AiResponseMode = Literal["standard", "stream"]


class AiConversationCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    topic: AiTopic


class AiConversationRenameRequest(BaseModel):
    title: str = Field(min_length=1, max_length=160)

    @field_validator("title")
    @classmethod
    def normalize_title(cls, title: str) -> str:
        normalized = title.strip()
        if not normalized:
            raise ValueError("Conversation title cannot be empty / 会话名称不能为空")
        return normalized


class AiMessageCreateRequest(BaseModel):
    content: str = Field(min_length=1, max_length=6000)
    model_tier: AiModelTier = "standard"
    response_mode: AiResponseMode = "standard"

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
    cycle_started_at: datetime
    cycle_ends_at: datetime
    cycle_credit_limit: int
    cycle_credits_used: int


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
