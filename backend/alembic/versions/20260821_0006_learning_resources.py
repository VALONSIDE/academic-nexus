"""add learning-resource catalog and mentor upload quotas

Revision ID: 20260821_0006
Revises: 20260821_0005
Create Date: 2026-08-21
"""

from alembic import op
import sqlalchemy as sa


revision = "20260821_0006"
down_revision = "20260821_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "resources",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("owner_user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("resource_type", sa.String(length=16), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("topics", sa.JSON(), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("external_url", sa.String(length=2048), nullable=True),
        sa.Column("file_storage_key", sa.String(length=255), nullable=True, unique=True),
        sa.Column("file_original_name", sa.String(length=255), nullable=True),
        sa.Column("file_content_type", sa.String(length=120), nullable=True),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("resource_type IN ('course', 'paper', 'book')", name="ck_resources_resource_type"),
    )
    op.create_index("ix_resources_tenant_id", "resources", ["tenant_id"])
    op.create_index("ix_resources_owner_user_id", "resources", ["owner_user_id"])
    op.create_index("ix_resources_resource_type", "resources", ["resource_type"])
    op.create_index("ix_resources_is_published", "resources", ["is_published"])
    op.create_index("ix_resources_created_at", "resources", ["created_at"])
    op.create_table(
        "courses",
        sa.Column("resource_id", sa.Uuid(), sa.ForeignKey("resources.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("provider", sa.String(length=160), nullable=True),
        sa.Column("level", sa.String(length=80), nullable=True),
        sa.Column("duration", sa.String(length=80), nullable=True),
    )
    op.create_table(
        "papers",
        sa.Column("resource_id", sa.Uuid(), sa.ForeignKey("resources.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("authors", sa.String(length=800), nullable=True),
        sa.Column("publication", sa.String(length=400), nullable=True),
        sa.Column("doi", sa.String(length=200), nullable=True),
        sa.Column("publication_year", sa.Integer(), nullable=True),
    )
    op.create_table(
        "books",
        sa.Column("resource_id", sa.Uuid(), sa.ForeignKey("resources.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("authors", sa.String(length=800), nullable=True),
        sa.Column("publisher", sa.String(length=400), nullable=True),
        sa.Column("isbn", sa.String(length=64), nullable=True),
        sa.Column("publication_year", sa.Integer(), nullable=True),
    )
    op.create_table(
        "mentor_resource_quotas",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("quota_bytes", sa.Integer(), nullable=False),
        sa.Column("used_bytes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_mentor_resource_quotas_user_id", "mentor_resource_quotas", ["user_id"])


def downgrade() -> None:
    op.drop_table("mentor_resource_quotas")
    op.drop_table("books")
    op.drop_table("papers")
    op.drop_table("courses")
    op.drop_table("resources")
