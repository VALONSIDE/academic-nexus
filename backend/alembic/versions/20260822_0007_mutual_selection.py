"""add mentor mutual-selection workflow

Revision ID: 20260822_0007
Revises: 20260821_0006
Create Date: 2026-08-22
"""

from alembic import op
import sqlalchemy as sa

revision = "20260822_0007"
down_revision = "20260821_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("selection_settings", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, unique=True), sa.Column("is_open", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("default_capacity", sa.Integer(), nullable=False, server_default="5"), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.CheckConstraint("default_capacity >= 1 AND default_capacity <= 200", name="ck_selection_default_capacity"))
    op.create_table("mentor_selection_settings", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("mentor_user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True), sa.Column("capacity", sa.Integer(), nullable=True), sa.Column("selection_mode", sa.String(length=20), nullable=False, server_default="manual"), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.CheckConstraint("capacity IS NULL OR (capacity >= 1 AND capacity <= 200)", name="ck_mentor_selection_capacity"), sa.CheckConstraint("selection_mode IN ('manual', 'first_come')", name="ck_mentor_selection_mode"))
    op.create_index("ix_mentor_selection_settings_mentor_user_id", "mentor_selection_settings", ["mentor_user_id"])
    op.create_table("mentor_selections", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False), sa.Column("student_user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False), sa.Column("mentor_user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False), sa.Column("status", sa.String(length=24), nullable=False), sa.Column("student_note", sa.Text(), nullable=True), sa.Column("mentor_note", sa.Text(), nullable=True), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True), sa.UniqueConstraint("student_user_id", "mentor_user_id", name="uq_mentor_selections_student_mentor"), sa.CheckConstraint("status IN ('pending_student', 'pending_mentor', 'confirmed', 'rejected', 'cancelled')", name="ck_mentor_selection_status"))
    op.create_index("ix_mentor_selections_tenant_id", "mentor_selections", ["tenant_id"])
    op.create_index("ix_mentor_selections_student_user_id", "mentor_selections", ["student_user_id"])
    op.create_index("ix_mentor_selections_mentor_user_id", "mentor_selections", ["mentor_user_id"])
    op.create_index("ix_mentor_selections_status", "mentor_selections", ["status"])


def downgrade() -> None:
    op.drop_table("mentor_selections")
    op.drop_table("mentor_selection_settings")
    op.drop_table("selection_settings")
