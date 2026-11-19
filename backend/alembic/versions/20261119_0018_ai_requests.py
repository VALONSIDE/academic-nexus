"""AI request identities and atomic result linkage."""
import sqlalchemy as sa
from alembic import op

revision = "20261119_0018"
down_revision = "20261119_0017"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("ai_turn_requests",
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("request_id", sa.Uuid(), primary_key=True),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column("event_id", sa.Uuid(), sa.ForeignKey("ai_usage_events.id", ondelete="SET NULL"), nullable=True),
        sa.Column("user_message_id", sa.Uuid(), sa.ForeignKey("ai_messages.id", ondelete="SET NULL"), nullable=True),
        sa.Column("assistant_message_id", sa.Uuid(), sa.ForeignKey("ai_messages.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_index("ix_ai_turn_requests_event_id", "ai_turn_requests", ["event_id"])


def downgrade():
    op.drop_table("ai_turn_requests")
