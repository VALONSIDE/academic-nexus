"""Workspace notifications, subscription history and persisted AI cards."""
import sqlalchemy as sa
from alembic import op

revision = "20261119_0020"
down_revision = "20261119_0019"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "workspace_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("recipient_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column("actor_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("institution_abbr", sa.String(12)),
        sa.Column("kind", sa.String(48), nullable=False),
        sa.Column("workspace", sa.String(12)),
        sa.Column("subject_id", sa.Uuid()),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_workspace_events_inbox", "workspace_events", ["tenant_id", "recipient_id", "created_at"])
    op.create_index("ix_workspace_events_history", "workspace_events", ["tenant_id", "institution_abbr", "created_at"])
    op.add_column("ai_messages", sa.Column("action_card", sa.JSON()))


def downgrade():
    op.drop_column("ai_messages", "action_card")
    op.drop_table("workspace_events")
