"""record AI credit cost per usage event

Revision ID: 20260823_0011
Revises: 20260823_0010
Create Date: 2026-08-23
"""

from alembic import op
import sqlalchemy as sa


revision = "20260823_0011"
down_revision = "20260823_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ai_usage_events",
        sa.Column("credit_cost", sa.Integer(), nullable=False, server_default="1"),
    )
    op.alter_column("ai_usage_events", "credit_cost", server_default=None)


def downgrade() -> None:
    op.drop_column("ai_usage_events", "credit_cost")
