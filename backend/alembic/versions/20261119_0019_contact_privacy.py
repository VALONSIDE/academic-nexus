"""Contact visibility and reissue-only activation receipts."""
import sqlalchemy as sa
from alembic import op

revision = "20261119_0019"
down_revision = "20261119_0018"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("wechat", sa.String(64), nullable=True))
    for field in ("share_email", "share_phone", "share_wechat"):
        op.add_column("users", sa.Column(field, sa.Boolean(), server_default=sa.false(), nullable=False))
    op.drop_column("pre_registrations", "access_key_encrypted")


def downgrade():
    op.add_column("pre_registrations", sa.Column("access_key_encrypted", sa.String(512), nullable=True))
    for field in ("share_wechat", "share_phone", "share_email", "wechat"):
        op.drop_column("users", field)
