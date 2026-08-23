import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.api.v1.endpoints.ai import _quota_response, rename_ai_conversation
from app.db.base import Base
from app.models import ai, tenant, user  # noqa: F401
from app.models.ai import AiConversation
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.ai import AiConversationRenameRequest, AiMessageCreateRequest
from app.services.ai.assistant import create_conversation, model_profile
from app.services.ai.quota import AiQuotaExceededError, quota_snapshot, release_ai_call, reserve_ai_call, update_user_quota


def test_subscription_balance_is_reserved_transactionally() -> None:
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

        update_user_quota(db, user_id=account.id, daily_limit=10, credit_balance=2)
        event = reserve_ai_call(db, account, conversation.id)
        assert event.status == "reserved"
        snapshot = quota_snapshot(db, account.id)
        assert snapshot.daily_remaining == 1
        assert snapshot.credit_balance == 1
        reserve_ai_call(db, account, conversation.id)
        with pytest.raises(AiQuotaExceededError, match="credit_balance_exhausted"):
            reserve_ai_call(db, account, conversation.id)


def test_ai_quota_response_includes_all_subscription_cycle_fields() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        organization = Tenant(slug="ai-cycle-response", name="AI Cycle Response")
        db.add(organization)
        db.flush()
        account = User(tenant_id=organization.id, username="AI_S105", full_name="AI User", password_hash="hash")
        db.add(account)
        db.commit()

        snapshot = quota_snapshot(db, account.id)
        response = _quota_response(snapshot)
        assert response.cycle_started_at == snapshot.cycle_started_at
        assert response.cycle_ends_at == snapshot.cycle_ends_at
        assert response.cycle_credit_limit == snapshot.cycle_credit_limit
        assert response.cycle_credits_used == snapshot.cycle_credits_used


def test_conversation_title_can_be_renamed_through_the_api() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        organization = Tenant(slug="rename-test", name="Rename Test")
        db.add(organization)
        db.flush()
        account = User(tenant_id=organization.id, username="AI_S101", full_name="AI User", password_hash="hash")
        db.add(account)
        db.flush()

        conversation = create_conversation(db, account, topic="academic_planning")
        assert conversation.title == "New conversation"

        renamed = rename_ai_conversation(
            conversation.id,
            AiConversationRenameRequest(title="Graduate school plan"),
            db,
            account,
        )
        assert renamed.title == "Graduate school plan"


def test_conversation_title_cannot_be_blank() -> None:
    with pytest.raises(ValidationError, match="会话名称不能为空"):
        AiConversationRenameRequest(title="   ")


def test_model_tiers_define_the_requested_credit_costs() -> None:
    assert model_profile("light").credit_cost == 1
    assert model_profile("standard").credit_cost == 1
    assert model_profile("expert").credit_cost == 2
    payload = AiMessageCreateRequest(content="Help me plan a literature review", model_tier="expert", response_mode="stream")
    assert payload.model_tier == "expert"
    assert payload.response_mode == "stream"


def test_expert_model_reserves_and_refunds_two_credits() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        organization = Tenant(slug="expert-tier-test", name="Expert Tier Test")
        db.add(organization)
        db.flush()
        account = User(tenant_id=organization.id, username="AI_S102", full_name="AI User", password_hash="hash")
        db.add(account)
        db.flush()
        conversation = AiConversation(tenant_id=organization.id, user_id=account.id, topic="academic_planning", title="Test")
        db.add(conversation)
        db.commit()

        update_user_quota(db, user_id=account.id, daily_limit=3, credit_balance=3)
        event = reserve_ai_call(db, account, conversation.id, model="MiniMax-M3", credit_cost=2)
        assert event.model == "MiniMax-M3"
        assert event.credit_cost == 2
        reserved = quota_snapshot(db, account.id)
        assert reserved.daily_used == 2
        assert reserved.credit_balance == 1

        release_ai_call(db, event.id, error_code="provider_request_failed")
        refunded = quota_snapshot(db, account.id)
        assert refunded.daily_used == 0
        assert refunded.credit_balance == 3
