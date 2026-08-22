"""backfill roles for activated accounts

Revision ID: 20260821_0003
Revises: 20260821_0002
Create Date: 2026-08-21 00:45:00
"""

from alembic import op


revision = "20260821_0003"
down_revision = "20260821_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Defensive backfill for an account activated before the role attachment was added.
    op.execute(
        """
        INSERT INTO user_roles (user_id, role_id)
        SELECT u.id, r.id
        FROM users u
        JOIN pre_registrations p ON p.id = u.pre_registration_id
        JOIN roles r ON r.tenant_id = u.tenant_id AND r.code = p.role_code
        LEFT JOIN user_roles ur ON ur.user_id = u.id AND ur.role_id = r.id
        WHERE ur.user_id IS NULL
        """
    )


def downgrade() -> None:
    # Role assignment is part of the activated account's data and is not removed on downgrade.
    pass
