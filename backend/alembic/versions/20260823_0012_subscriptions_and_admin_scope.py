"""add subscription cycles, premium keys, and institution admin scopes

Revision ID: 20260823_0012
Revises: 20260823_0011
Create Date: 2026-08-23
"""

from calendar import monthrange
from datetime import timezone
import uuid

from alembic import op
import sqlalchemy as sa


revision = "20260823_0012"
down_revision = "20260823_0011"
branch_labels = None
depends_on = None


def _add_month(value):
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    year = value.year + (value.month // 12)
    month = value.month % 12 + 1
    return value.replace(year=year, month=month, day=min(value.day, monthrange(year, month)[1]))


def upgrade() -> None:
    op.create_table(
        "ai_user_subscriptions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("plan_code", sa.String(length=16), nullable=False, server_default="basic"),
        sa.Column("cycle_started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("cycle_ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("credit_limit", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("plan_code IN ('basic', 'pro', 'ultra', 'max')", name="ck_ai_user_subscriptions_plan_code"),
        sa.CheckConstraint("credit_limit >= 0", name="ck_ai_user_subscriptions_credit_limit"),
        sa.CheckConstraint("cycle_ends_at > cycle_started_at", name="ck_ai_user_subscriptions_cycle_order"),
    )
    op.create_index("ix_ai_user_subscriptions_user_id", "ai_user_subscriptions", ["user_id"])
    op.create_table(
        "institution_subscription_allocations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("institution_abbr", sa.String(length=12), nullable=False),
        sa.Column("institution_name_zh", sa.String(length=160), nullable=False),
        sa.Column("pro_credits", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ultra_credits", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_credits", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "institution_abbr", name="uq_subscription_allocation_institution"),
        sa.CheckConstraint("pro_credits >= 0", name="ck_subscription_allocation_pro_credits"),
        sa.CheckConstraint("ultra_credits >= 0", name="ck_subscription_allocation_ultra_credits"),
        sa.CheckConstraint("max_credits >= 0", name="ck_subscription_allocation_max_credits"),
    )
    op.create_index("ix_institution_subscription_allocations_tenant_id", "institution_subscription_allocations", ["tenant_id"])
    op.create_table(
        "institution_admin_scopes",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("institution_abbr", sa.String(length=12), nullable=False),
        sa.Column("institution_name_zh", sa.String(length=160), nullable=False),
        sa.Column("assigned_by_user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "user_id", "institution_abbr", name="uq_institution_admin_scope"),
    )
    op.create_index("ix_institution_admin_scopes_tenant_id", "institution_admin_scopes", ["tenant_id"])
    op.create_index("ix_institution_admin_scopes_user_id", "institution_admin_scopes", ["user_id"])
    op.create_table(
        "premium_subscription_keys",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("institution_abbr", sa.String(length=12), nullable=False),
        sa.Column("institution_name_zh", sa.String(length=160), nullable=False),
        sa.Column("plan_code", sa.String(length=16), nullable=False),
        sa.Column("key_hash", sa.String(length=255), nullable=False),
        sa.Column("key_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="issued"),
        sa.Column("issued_by_user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("activated_by_user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("key_fingerprint", name="uq_premium_subscription_keys_fingerprint"),
        sa.CheckConstraint("plan_code IN ('pro', 'ultra', 'max')", name="ck_premium_subscription_keys_plan_code"),
        sa.CheckConstraint("status IN ('issued', 'activated', 'revoked')", name="ck_premium_subscription_keys_status"),
    )
    op.create_index("ix_premium_subscription_keys_tenant_id", "premium_subscription_keys", ["tenant_id"])
    op.create_index("ix_premium_subscription_keys_institution_abbr", "premium_subscription_keys", ["institution_abbr"])
    op.create_index("ix_premium_subscription_keys_status", "premium_subscription_keys", ["status"])

    # Existing accounts keep their registration date as the first normal-plan
    # cycle day. The first entitlement read catches up elapsed cycles safely.
    connection = op.get_bind()
    rows = connection.execute(sa.text("SELECT id, created_at FROM users")).mappings().all()
    table = sa.table(
        "ai_user_subscriptions",
        sa.column("id", sa.Uuid()),
        sa.column("user_id", sa.Uuid()),
        sa.column("plan_code", sa.String()),
        sa.column("cycle_started_at", sa.DateTime(timezone=True)),
        sa.column("cycle_ends_at", sa.DateTime(timezone=True)),
        sa.column("credit_limit", sa.Integer()),
    )
    for row in rows:
        started_at = row["created_at"]
        connection.execute(
            table.insert().values(
                id=uuid.uuid4(),
                user_id=row["id"],
                plan_code="basic",
                cycle_started_at=started_at,
                cycle_ends_at=_add_month(started_at),
                credit_limit=10,
            )
        )
    op.execute("UPDATE ai_user_quotas SET plan_code = 'basic', daily_limit = 10, credit_balance = 10")


def downgrade() -> None:
    op.drop_table("premium_subscription_keys")
    op.drop_table("institution_admin_scopes")
    op.drop_table("institution_subscription_allocations")
    op.drop_table("ai_user_subscriptions")
