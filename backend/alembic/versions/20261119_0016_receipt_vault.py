"""Encrypted recoverable unactivated receipts."""
import sqlalchemy as sa
from alembic import op

revision = "20261119_0016"
down_revision = "20260917_0015"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("pre_registrations", sa.Column("access_key_encrypted", sa.String(512), nullable=True))


def downgrade():
    op.drop_column("pre_registrations", "access_key_encrypted")
