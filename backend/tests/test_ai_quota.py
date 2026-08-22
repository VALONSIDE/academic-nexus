import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models import ai, tenant, user  # noqa: F401
from app.models.ai import AiConversation
from app.models.tenant import Tenant
from app.models.user import User
from app.services.ai.quota import AiQuotaExceededError, quota_snapshot, reserve_ai_call, update_user_quota


def test_user_daily_limit_and_balance_are_reserved_transactionally() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        organization = Tenant(slug="ai-test", name="AI Test")
        db.add(organization)
        db.flush()
        account = User(tenant_id=organization.id, username="AI_S100", full_name="AI User", password_hash="hash")
        db.add(account)
        db.flush()
        conversation = AiConversation(tenant_id=organization.id, user_id=account.id, topic="academic_planning", title="Test")
        db.add(conversation)
        db.commit()

        update_user_quota(db, user_id=account.id, daily_limit=1, credit_balance=2)
        event = reserve_ai_call(db, account, conversation.id)
        assert event.status == "reserved"
        snapshot = quota_snapshot(db, account.id)
        assert snapshot.daily_used == 1
        assert snapshot.daily_remaining == 0
        assert snapshot.credit_balance == 1
        with pytest.raises(AiQuotaExceededError, match="user_daily_limit_reached"):
            reserve_ai_call(db, account, conversation.id)
