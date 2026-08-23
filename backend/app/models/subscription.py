"""Institution-scoped premium-subscription inventory and key entities."""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class InstitutionSubscriptionAllocation(Base):
    """Unspent premium-key inventory allocated by a super administrator."""

    __tablename__ = "institution_subscription_allocations"
    __table_args__ = (
        UniqueConstraint("tenant_id", "institution_abbr", name="uq_subscription_allocation_institution"),
        CheckConstraint("pro_credits >= 0", name="ck_subscription_allocation_pro_credits"),
        CheckConstraint("ultra_credits >= 0", name="ck_subscription_allocation_ultra_credits"),
        CheckConstraint("max_credits >= 0", name="ck_subscription_allocation_max_credits"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    institution_abbr: Mapped[str] = mapped_column(String(12))
    institution_name_zh: Mapped[str] = mapped_column(String(160))
    pro_credits: Mapped[int] = mapped_column(Integer, default=0)
    ultra_credits: Mapped[int] = mapped_column(Integer, default=0)
    max_credits: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class InstitutionAdminScope(Base):
    """An institution administrator can be assigned one or more institutions."""

    __tablename__ = "institution_admin_scopes"
    __table_args__ = (
        UniqueConstraint("tenant_id", "user_id", "institution_abbr", name="uq_institution_admin_scope"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    institution_abbr: Mapped[str] = mapped_column(String(12))
    institution_name_zh: Mapped[str] = mapped_column(String(160))
    assigned_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PremiumSubscriptionKey(Base):
    """One-time institution-bound premium subscription key; plaintext is never stored."""

    __tablename__ = "premium_subscription_keys"
    __table_args__ = (
        UniqueConstraint("key_fingerprint", name="uq_premium_subscription_keys_fingerprint"),
        CheckConstraint("plan_code IN ('pro', 'ultra', 'max')", name="ck_premium_subscription_keys_plan_code"),
        CheckConstraint("status IN ('issued', 'activated', 'revoked')", name="ck_premium_subscription_keys_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    institution_abbr: Mapped[str] = mapped_column(String(12), index=True)
    institution_name_zh: Mapped[str] = mapped_column(String(160))
    plan_code: Mapped[str] = mapped_column(String(16))
    key_hash: Mapped[str] = mapped_column(String(255))
    key_fingerprint: Mapped[str] = mapped_column(String(64), unique=True)
    status: Mapped[str] = mapped_column(String(16), default="issued", index=True)
    issued_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    activated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
