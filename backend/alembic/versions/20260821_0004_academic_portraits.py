"""add phase 2 academic portrait fields

Revision ID: 20260821_0004
Revises: 20260821_0003
Create Date: 2026-08-21
"""

from alembic import op
import sqlalchemy as sa


revision = "20260821_0004"
down_revision = "20260821_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("student_profiles", sa.Column("research_interests", sa.JSON(), nullable=True))
    op.add_column("student_profiles", sa.Column("skills", sa.JSON(), nullable=True))
    op.add_column("student_profiles", sa.Column("academic_performance", sa.Text(), nullable=True))
    op.add_column("student_profiles", sa.Column("academic_goals", sa.Text(), nullable=True))
    op.add_column("student_profiles", sa.Column("research_experience", sa.Text(), nullable=True))
    op.add_column("student_profiles", sa.Column("profile_completed_at", sa.DateTime(timezone=True), nullable=True))

    op.add_column("mentor_profiles", sa.Column("research_directions", sa.JSON(), nullable=True))
    op.add_column("mentor_profiles", sa.Column("representative_papers", sa.JSON(), nullable=True))
    op.add_column("mentor_profiles", sa.Column("research_projects", sa.Text(), nullable=True))
    op.add_column("mentor_profiles", sa.Column("mentoring_style", sa.Text(), nullable=True))
    op.add_column("mentor_profiles", sa.Column("profile_completed_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("mentor_profiles", "profile_completed_at")
    op.drop_column("mentor_profiles", "mentoring_style")
    op.drop_column("mentor_profiles", "research_projects")
    op.drop_column("mentor_profiles", "representative_papers")
    op.drop_column("mentor_profiles", "research_directions")
    op.drop_column("student_profiles", "profile_completed_at")
    op.drop_column("student_profiles", "research_experience")
    op.drop_column("student_profiles", "academic_goals")
    op.drop_column("student_profiles", "academic_performance")
    op.drop_column("student_profiles", "skills")
    op.drop_column("student_profiles", "research_interests")
