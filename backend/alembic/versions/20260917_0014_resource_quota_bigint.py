"""Support the full 2048 MB storage allowance without integer overflow."""

from alembic import op
import sqlalchemy as sa

revision = "20260917_0014"
down_revision = "20260823_0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for column in ("quota_bytes", "used_bytes"):
        op.alter_column("mentor_resource_quotas", column, existing_type=sa.Integer(), type_=sa.BigInteger(), existing_nullable=False)


def downgrade() -> None:
    # PostgreSQL refuses overflow instead of silently truncating a stored quota.
    for column in ("quota_bytes", "used_bytes"):
        op.alter_column("mentor_resource_quotas", column, existing_type=sa.BigInteger(), type_=sa.Integer(), existing_nullable=False)
