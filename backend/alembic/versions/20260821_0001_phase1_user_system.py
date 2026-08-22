"""phase 1 user system

Revision ID: 20260821_0001
Revises:
Create Date: 2026-08-21 00:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260821_0001"
down_revision = None
branch_labels = None
depends_on = None


def uuid_column(*, primary_key: bool = False, nullable: bool = False) -> sa.Column:
    return sa.Column("id", sa.Uuid(), primary_key=primary_key, nullable=nullable)


def timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    ]


def upgrade() -> None:
    # Reserved for Phase 4 RAG; harmless if already enabled.
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "tenants",
        uuid_column(primary_key=True),
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        *timestamps(),
        sa.UniqueConstraint("slug", name="uq_tenants_slug"),
    )
    op.create_table(
        "roles",
        uuid_column(primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name_zh", sa.String(length=64), nullable=False),
        sa.Column("name_en", sa.String(length=64), nullable=False),
        *timestamps(),
        sa.UniqueConstraint("tenant_id", "code", name="uq_roles_tenant_code"),
    )
    op.create_table(
        "users",
        uuid_column(primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("full_name", sa.String(length=120), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("preferred_locale", sa.String(length=10), nullable=False, server_default="zh-CN"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        *timestamps(),
        sa.UniqueConstraint("tenant_id", "email", name="uq_users_tenant_email"),
    )
    op.create_index("ix_users_tenant_id", "users", ["tenant_id"])
    op.create_table(
        "user_roles",
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("role_id", sa.Uuid(), sa.ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )
    op.create_table(
        "student_profiles",
        uuid_column(primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("student_no", sa.String(length=64), nullable=True),
        sa.Column("university", sa.String(length=160), nullable=True),
        sa.Column("department", sa.String(length=160), nullable=True),
        sa.Column("major", sa.String(length=160), nullable=True),
        sa.Column("grade", sa.String(length=32), nullable=True),
        *timestamps(),
        sa.UniqueConstraint("user_id", name="uq_student_profiles_user_id"),
    )
    op.create_table(
        "mentor_profiles",
        uuid_column(primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("employee_no", sa.String(length=64), nullable=True),
        sa.Column("university", sa.String(length=160), nullable=True),
        sa.Column("department", sa.String(length=160), nullable=True),
        sa.Column("title", sa.String(length=120), nullable=True),
        *timestamps(),
        sa.UniqueConstraint("user_id", name="uq_mentor_profiles_user_id"),
    )


def downgrade() -> None:
    op.drop_table("mentor_profiles")
    op.drop_table("student_profiles")
    op.drop_table("user_roles")
    op.drop_index("ix_users_tenant_id", table_name="users")
    op.drop_table("users")
    op.drop_table("roles")
    op.drop_table("tenants")
