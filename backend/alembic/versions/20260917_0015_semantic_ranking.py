"""Add tenant-scoped vector and rerank caches."""

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision = "20260917_0015"
down_revision = "20260917_0014"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    for table, column, index in (
        ("ranking_embeddings", sa.Column("embedding", Vector(1024), nullable=False), "ix_ranking_embeddings_expiry"),
        ("ranking_rerank_cache", sa.Column("scores", sa.JSON(), nullable=False), "ix_ranking_rerank_expiry"),
    ):
        op.create_table(table,
                        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), primary_key=True),
                        sa.Column("fingerprint", sa.String(64), primary_key=True),
                        column, sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False))
        op.create_index(index, table, ["tenant_id", "expires_at"])


def downgrade():
    op.drop_table("ranking_rerank_cache")
    op.drop_table("ranking_embeddings")
