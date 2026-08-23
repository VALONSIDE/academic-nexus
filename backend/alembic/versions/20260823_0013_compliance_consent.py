"""add legal-document acceptance evidence

Revision ID: 20260823_0013
Revises: 20260823_0012
Create Date: 2026-08-23
"""

from alembic import op
import sqlalchemy as sa


revision = "20260823_0013"
down_revision = "20260823_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("terms_accepted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("privacy_accepted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("legal_document_version", sa.String(length=32), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "legal_document_version")
    op.drop_column("users", "privacy_accepted_at")
    op.drop_column("users", "terms_accepted_at")
