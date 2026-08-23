import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PreRegistrationBatch(Base):
    """One validated partner-school Excel import / 一次通过校验的合作院校 Excel 导入。"""

    __tablename__ = "pre_registration_batches"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    uploaded_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    source_filename: Mapped[str] = mapped_column(String(255))
    row_count: Mapped[int] = mapped_column(Integer)
    receipt_issued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PreRegistration(Base):
    """Immutable partner-provided identity and one-time Access Key / 合作院校身份与一次性激活码。"""

    __tablename__ = "pre_registrations"
    __table_args__ = (
        CheckConstraint("role_code IN ('student', 'mentor')", name="ck_pre_registrations_role_code"),
        CheckConstraint("status IN ('issued', 'activated', 'revoked')", name="ck_pre_registrations_status"),
        UniqueConstraint("tenant_id", "username", name="uq_pre_registrations_tenant_username"),
        UniqueConstraint("username", name="uq_pre_registrations_username_global"),
        UniqueConstraint("access_key_fingerprint", name="uq_pre_registrations_access_key_fingerprint"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    batch_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("pre_registration_batches.id", ondelete="RESTRICT"), index=True)
    username: Mapped[str] = mapped_column(String(100))
    role_code: Mapped[str] = mapped_column(String(16))
    full_name: Mapped[str] = mapped_column(String(120))
    academic_id: Mapped[str] = mapped_column(String(64))
    institution_abbr: Mapped[str] = mapped_column(String(12))
    institution_name_zh: Mapped[str] = mapped_column(String(160))
    college_name_zh: Mapped[str] = mapped_column(String(160))
    access_key_hash: Mapped[str] = mapped_column(String(255))
    access_key_fingerprint: Mapped[str] = mapped_column(String(64), unique=True)
    status: Mapped[str] = mapped_column(String(16), default="issued")
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
