"""Shared authentication limits and administrator audit."""
import sqlalchemy as sa
from alembic import op

revision = "20261119_0017"
down_revision = "20261119_0016"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("security_audit", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("actor_id", sa.Uuid(), nullable=True), sa.Column("tenant_id", sa.Uuid(), nullable=True), sa.Column("method", sa.String(10), nullable=False), sa.Column("path", sa.String(255), nullable=False), sa.Column("status", sa.Integer(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    for name in ("actor_id", "tenant_id", "created_at"):
        op.create_index(f"ix_security_audit_{name}", "security_audit", [name])
    op.create_table("security_rate_buckets", sa.Column("key", sa.String(64), primary_key=True), sa.Column("window", sa.Integer(), primary_key=True), sa.Column("count", sa.Integer(), nullable=False))


def downgrade():
    op.drop_table("security_rate_buckets")
    op.drop_table("security_audit")
