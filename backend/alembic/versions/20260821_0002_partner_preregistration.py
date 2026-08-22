"""partner institution preregistration and Access Key activation

Revision ID: 20260821_0002
Revises: 20260821_0001
Create Date: 2026-08-21 00:30:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260821_0002"
down_revision = "20260821_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pre_registration_batches",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("uploaded_by_user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("source_filename", sa.String(length=255), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=False),
        sa.Column("receipt_issued_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )
    op.create_table(
        "pre_registrations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("batch_id", sa.Uuid(), sa.ForeignKey("pre_registration_batches.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("username", sa.String(length=100), nullable=False),
        sa.Column("role_code", sa.String(length=16), nullable=False),
        sa.Column("full_name", sa.String(length=120), nullable=False),
        sa.Column("academic_id", sa.String(length=64), nullable=False),
        sa.Column("institution_abbr", sa.String(length=12), nullable=False),
        sa.Column("access_key_hash", sa.String(length=255), nullable=False),
        sa.Column("access_key_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="issued"),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint("role_code IN ('student', 'mentor')", name="ck_pre_registrations_role_code"),
        sa.CheckConstraint("status IN ('issued', 'activated', 'revoked')", name="ck_pre_registrations_status"),
        sa.UniqueConstraint("tenant_id", "username", name="uq_pre_registrations_tenant_username"),
        sa.UniqueConstraint("access_key_fingerprint", name="uq_pre_registrations_access_key_fingerprint"),
    )
    op.create_index("ix_pre_registrations_tenant_status", "pre_registrations", ["tenant_id", "status"])
    op.add_column("users", sa.Column("username", sa.String(length=100), nullable=True))
    op.add_column("users", sa.Column("pre_registration_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_users_pre_registration_id",
        "users",
        "pre_registrations",
        ["pre_registration_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_unique_constraint("uq_users_tenant_username", "users", ["tenant_id", "username"])
    op.create_unique_constraint("uq_users_pre_registration_id", "users", ["pre_registration_id"])
    op.alter_column("users", "email", existing_type=sa.String(length=320), nullable=True)


def downgrade() -> None:
    op.alter_column("users", "email", existing_type=sa.String(length=320), nullable=False)
    op.drop_constraint("uq_users_pre_registration_id", "users", type_="unique")
    op.drop_constraint("uq_users_tenant_username", "users", type_="unique")
    op.drop_constraint("fk_users_pre_registration_id", "users", type_="foreignkey")
    op.drop_column("users", "pre_registration_id")
    op.drop_column("users", "username")
    op.drop_index("ix_pre_registrations_tenant_status", table_name="pre_registrations")
    op.drop_table("pre_registrations")
    op.drop_table("pre_registration_batches")
