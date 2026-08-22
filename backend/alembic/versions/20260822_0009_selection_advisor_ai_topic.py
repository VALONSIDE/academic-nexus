"""add selection-advisor AI conversation topic

Revision ID: 20260822_0009
Revises: 20260822_0008
Create Date: 2026-08-22
"""

from alembic import op
import sqlalchemy as sa


revision = "20260822_0009"
down_revision = "20260822_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ck_ai_conversations_topic", "ai_conversations", type_="check")
    op.create_check_constraint(
        "ck_ai_conversations_topic",
        "ai_conversations",
        "topic IN ('academic_planning', 'mentor_consultation', 'learning_roadmap', 'selection_advisor')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_ai_conversations_topic", "ai_conversations", type_="check")
    op.create_check_constraint(
        "ck_ai_conversations_topic",
        "ai_conversations",
        "topic IN ('academic_planning', 'mentor_consultation', 'learning_roadmap')",
    )
