"""Tenant-scoped, content-addressed semantic caches. No source text or keys."""

from datetime import datetime
from uuid import UUID

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RankingEmbedding(Base):
    __tablename__ = "ranking_embeddings"
    __table_args__ = (Index("ix_ranking_embeddings_expiry", "tenant_id", "expires_at"),)

    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), primary_key=True)
    fingerprint: Mapped[str] = mapped_column(String(64), primary_key=True)
    embedding: Mapped[list[float]] = mapped_column(Vector(1024).with_variant(JSON(), "sqlite"))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class RankingRerankCache(Base):
    __tablename__ = "ranking_rerank_cache"
    __table_args__ = (Index("ix_ranking_rerank_expiry", "tenant_id", "expires_at"),)

    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), primary_key=True)
    fingerprint: Mapped[str] = mapped_column(String(64), primary_key=True)
    scores: Mapped[list[float]] = mapped_column(JSON)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
