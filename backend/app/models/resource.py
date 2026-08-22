"""Learning-resource catalog, metadata specializations, and mentor storage quotas."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Resource(Base):
    __tablename__ = "resources"
    __table_args__ = (CheckConstraint("resource_type IN ('course', 'paper', 'book')", name="ck_resources_resource_type"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    owner_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    resource_type: Mapped[str] = mapped_column(String(16), index=True)
    title: Mapped[str] = mapped_column(String(240))
    description: Mapped[str] = mapped_column(Text, default="")
    topics: Mapped[list[str]] = mapped_column(JSON, default=list)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    external_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    file_storage_key: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)
    file_original_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_content_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    file_size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    is_published: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    course: Mapped["Course | None"] = relationship(back_populates="resource", uselist=False, cascade="all, delete-orphan")
    paper: Mapped["Paper | None"] = relationship(back_populates="resource", uselist=False, cascade="all, delete-orphan")
    book: Mapped["Book | None"] = relationship(back_populates="resource", uselist=False, cascade="all, delete-orphan")


class Course(Base):
    __tablename__ = "courses"

    resource_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("resources.id", ondelete="CASCADE"), primary_key=True)
    provider: Mapped[str | None] = mapped_column(String(160), nullable=True)
    level: Mapped[str | None] = mapped_column(String(80), nullable=True)
    duration: Mapped[str | None] = mapped_column(String(80), nullable=True)
    resource: Mapped[Resource] = relationship(back_populates="course")


class Paper(Base):
    __tablename__ = "papers"

    resource_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("resources.id", ondelete="CASCADE"), primary_key=True)
    authors: Mapped[str | None] = mapped_column(String(800), nullable=True)
    publication: Mapped[str | None] = mapped_column(String(400), nullable=True)
    doi: Mapped[str | None] = mapped_column(String(200), nullable=True)
    publication_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    resource: Mapped[Resource] = relationship(back_populates="paper")


class Book(Base):
    __tablename__ = "books"

    resource_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("resources.id", ondelete="CASCADE"), primary_key=True)
    authors: Mapped[str | None] = mapped_column(String(800), nullable=True)
    publisher: Mapped[str | None] = mapped_column(String(400), nullable=True)
    isbn: Mapped[str | None] = mapped_column(String(64), nullable=True)
    publication_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    resource: Mapped[Resource] = relationship(back_populates="book")


class MentorResourceQuota(Base):
    __tablename__ = "mentor_resource_quotas"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True)
    quota_bytes: Mapped[int] = mapped_column(Integer)
    used_bytes: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
