"""add required Chinese institution identity and selection exceptions

Revision ID: 20260822_0008
Revises: 20260822_0007
Create Date: 2026-08-22
"""

from alembic import op
import sqlalchemy as sa

revision = "20260822_0008"
down_revision = "20260822_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("pre_registrations", sa.Column("institution_name_zh", sa.String(length=160), nullable=False, server_default=""))
    op.add_column("pre_registrations", sa.Column("college_name_zh", sa.String(length=160), nullable=False, server_default=""))
    op.add_column("student_profiles", sa.Column("institution_abbr", sa.String(length=12), nullable=True))
    op.add_column("mentor_profiles", sa.Column("institution_abbr", sa.String(length=12), nullable=True))
    op.add_column("selection_settings", sa.Column("default_student_choice_limit", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("mentor_selection_settings", sa.Column("is_exempt", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.create_table(
        "student_selection_settings",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("student_user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("choice_limit", sa.Integer(), nullable=True),
        sa.Column("is_exempt", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("choice_limit IS NULL OR (choice_limit >= 1 AND choice_limit <= 50)", name="ck_student_choice_limit"),
    )
    op.create_index("ix_student_selection_settings_student_user_id", "student_selection_settings", ["student_user_id"])
    op.execute("UPDATE pre_registrations SET institution_name_zh = institution_abbr, college_name_zh = COALESCE(college_name_zh, '') WHERE institution_name_zh = ''")
    op.execute("UPDATE student_profiles SET institution_abbr = university WHERE institution_abbr IS NULL")
    op.execute("UPDATE mentor_profiles SET institution_abbr = university WHERE institution_abbr IS NULL")


def downgrade() -> None:
    op.drop_table("student_selection_settings")
    op.drop_column("mentor_selection_settings", "is_exempt")
    op.drop_column("selection_settings", "default_student_choice_limit")
    op.drop_column("mentor_profiles", "institution_abbr")
    op.drop_column("student_profiles", "institution_abbr")
    op.drop_column("pre_registrations", "college_name_zh")
    op.drop_column("pre_registrations", "institution_name_zh")
