"""API contracts for subscription-cycle and premium-key operations."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

PremiumPlan = Literal["pro", "ultra", "max"]
SubscriptionPlan = Literal["basic", "pro", "ultra", "max"]


def _normalize_abbr(value: str) -> str:
    normalized = value.strip().upper()
    if not normalized or len(normalized) > 12:
        raise ValueError("Institution abbreviation must contain 1 to 12 characters")
    return normalized


class SubscriptionResponse(BaseModel):
    plan_code: SubscriptionPlan
    credit_limit: int
    credit_balance: int
    credits_used: int
    cycle_started_at: datetime
    cycle_ends_at: datetime


class SubscriptionKeyActivateRequest(BaseModel):
    key: str = Field(min_length=13, max_length=13)

    @field_validator("key")
    @classmethod
    def normalize_key(cls, value: str) -> str:
        return value.strip().upper()


class InstitutionAllocationRequest(BaseModel):
    pro_credits: int = Field(ge=0, le=100000)
    ultra_credits: int = Field(ge=0, le=100000)
    max_credits: int = Field(ge=0, le=100000)


class InstitutionAllocationResponse(BaseModel):
    institution_abbr: str
    institution_name_zh: str
    pro_credits: int
    ultra_credits: int
    max_credits: int


class InstitutionAdminAssignRequest(BaseModel):
    user_id: UUID
    institution_abbr: str = Field(min_length=1, max_length=12)

    @field_validator("institution_abbr")
    @classmethod
    def normalize_abbr(cls, value: str) -> str:
        return _normalize_abbr(value)

class InstitutionAdminScopeResponse(BaseModel):
    id: UUID
    user_id: UUID
    username: str
    full_name: str
    institution_abbr: str
    institution_name_zh: str
    created_at: datetime


class InstitutionOptionResponse(BaseModel):
    institution_abbr: str
    institution_name_zh: str


class InstitutionAccountResponse(BaseModel):
    id: UUID
    username: str
    full_name: str
    role: Literal["student", "mentor"]
    has_active_premium_subscription: bool = False


class PremiumSubscriptionKeyIssueRequest(BaseModel):
    institution_abbr: str = Field(min_length=1, max_length=12)
    plan_code: PremiumPlan

    @field_validator("institution_abbr")
    @classmethod
    def normalize_abbr(cls, value: str) -> str:
        return _normalize_abbr(value)


class PremiumSubscriptionKeyBatchIssueRequest(PremiumSubscriptionKeyIssueRequest):
    quantity: int = Field(ge=1, le=1000)


class PremiumSubscriptionKeyResponse(BaseModel):
    id: UUID
    institution_abbr: str
    institution_name_zh: str
    plan_code: PremiumPlan
    status: Literal["issued", "activated", "revoked"]
    issued_at: datetime
    activated_at: datetime | None
    revoked_at: datetime | None


class SubscriptionKeyDeliveryValidationResponse(BaseModel):
    """Transient validation result.  ``key`` is never persisted by the API."""

    row_number: int
    key: str
    plan_code: PremiumPlan | None
    institution_abbr: str | None
    institution_name_zh: str | None
    status: Literal["available", "invalid", "unavailable", "not_authorized"]


class SubscriptionKeyDeliveryItemRequest(BaseModel):
    key: str = Field(min_length=13, max_length=13)
    recipient_user_id: UUID | None = None

    @field_validator("key")
    @classmethod
    def normalize_key(cls, value: str) -> str:
        normalized = value.strip().upper()
        if len(normalized) != 13:
            raise ValueError("Invalid subscription Key format")
        return normalized


class SubscriptionKeyDeliveryBatchRequest(BaseModel):
    items: list[SubscriptionKeyDeliveryItemRequest] = Field(min_length=1, max_length=300)


class SubscriptionKeyDeliveryActivationResponse(BaseModel):
    activated_count: int
