import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class WorkspaceEvent(Base):
    __tablename__ = "workspace_events"
    __table_args__ = (
        Index("ix_workspace_events_inbox", "tenant_id", "recipient_id", "created_at"),
        Index("ix_workspace_events_history", "tenant_id", "institution_abbr", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    recipient_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    institution_abbr: Mapped[str | None] = mapped_column(String(12))
    kind: Mapped[str] = mapped_column(String(48))
    workspace: Mapped[str | None] = mapped_column(String(12))
    subject_id: Mapped[uuid.UUID | None]
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
