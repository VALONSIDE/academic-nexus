"""harden session revocation and globally unique login names

Revision ID: 20260823_0010
Revises: 20260822_0009
Create Date: 2026-08-23
"""

from alembic import op
import sqlalchemy as sa


revision = "20260823_0010"
down_revision = "20260822_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("auth_version", sa.Integer(), nullable=False, server_default="0"))
    op.alter_column("users", "auth_version", server_default=None)
    op.create_unique_constraint("uq_users_username_global", "users", ["username"])
    op.create_unique_constraint("uq_pre_registrations_username_global", "pre_registrations", ["username"])


def downgrade() -> None:
    op.drop_constraint("uq_pre_registrations_username_global", "pre_registrations", type_="unique")
    op.drop_constraint("uq_users_username_global", "users", type_="unique")
    op.drop_column("users", "auth_version")
