import json
from io import BytesIO
from unittest.mock import patch

import httpx
import pytest
from fastapi import HTTPException
from openpyxl import load_workbook
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.api.v1.endpoints.auth import logout
from app.api.v1.endpoints.pre_registrations import reissue_receipts
from app.core.security import hash_password, verify_password
from app.db.base import Base
from app.models.pre_registration import PreRegistration, PreRegistrationBatch
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.pre_registration import PreRegistrationBulkDeleteRequest
from app.services.ai import providers
from app.services.ai.minimax import MiniMaxRequestError


def test_receipt_reissue_revokes_key_and_pending_registration_and_hides_activated_key():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        tenant = Tenant(slug="november", name="Test")
        db.add(tenant)
        db.flush()
        admin = User(tenant_id=tenant.id, username="ADMIN", full_name="Admin", password_hash="hash")
        db.add(admin)
        db.flush()
        batch = PreRegistrationBatch(tenant_id=tenant.id, uploaded_by_user_id=admin.id, source_filename="test.xlsx", row_count=1)
        db.add(batch)
        db.flush()
        item = PreRegistration(tenant_id=tenant.id, batch_id=batch.id, username="TEST_S1000", role_code="student", full_name="Test", academic_id="1000", institution_abbr="TEST", institution_name_zh="Test", college_name_zh="Test", access_key_hash=hash_password("old-key"), access_key_fingerprint="old", status="issued")
        db.add(item)
        db.flush()
        pending = User(tenant_id=tenant.id, username=item.username, full_name="Test", password_hash="hash", pre_registration_id=item.id, is_active=False)
        db.add(pending)
        db.commit()
        response = reissue_receipts(PreRegistrationBulkDeleteRequest(ids=[item.id]), db, admin)
        workbook = load_workbook(BytesIO(response.body))
        new_key = workbook.active.cell(2, 6).value
        workbook.close()
        assert verify_password(new_key, item.access_key_hash)
        assert not verify_password("old-key", item.access_key_hash)
        assert pending.auth_version == 1
        assert "no-store" in response.headers["cache-control"]
        other = Tenant(slug="other", name="Other")
        db.add(other)
        db.flush()
        stranger = User(tenant_id=other.id, full_name="Other", password_hash="hash")
        with pytest.raises(HTTPException) as forbidden:
            reissue_receipts(PreRegistrationBulkDeleteRequest(ids=[item.id]), db, stranger)
        assert forbidden.value.status_code == 404
        item.status = "activated"
        db.commit()
        with pytest.raises(HTTPException):
            reissue_receipts(PreRegistrationBulkDeleteRequest(ids=[item.id]), db, admin)
        logout(admin, db)
        assert admin.auth_version == 1


@pytest.mark.parametrize("stream", [False, True])
def test_deepseek_requests_and_final_content_only(monkeypatch, stream):
    from pydantic import SecretStr
    from app.core.config import get_settings
    monkeypatch.setattr(get_settings(), "deepseek_api_key", SecretStr("test"))
    monkeypatch.setattr(get_settings(), "deepseek_base_url", "https://api.deepseek.com")
    def handler(request):
        body = json.loads(request.content)
        assert str(request.url) == "https://api.deepseek.com/chat/completions"
        assert body["model"] == "deepseek-flash"
        assert body["thinking"] == {"type": "enabled"}
        assert body["max_tokens"] >= 8192
        if not stream:
            return httpx.Response(200, json={"choices": [{"message": {"content": "Answer", "reasoning_content": "private"}, "finish_reason": "stop"}], "usage": {"prompt_tokens": 7, "completion_tokens": 9}})
        events = [{"choices": [{"delta": {"reasoning_content": "private"}}]}, {"choices": [{"delta": {"content": "Answer"}, "finish_reason": "stop"}]}, {"choices": [], "usage": {"prompt_tokens": 7, "completion_tokens": 9}}]
        content = ": keepalive\n\n" + "".join("data: " + json.dumps(event) + "\n\n" for event in events) + "data: [DONE]\n\n"
        return httpx.Response(200, text=content)
    real_client = httpx.Client
    with patch.object(providers.httpx, "Client", side_effect=lambda **kw: real_client(transport=httpx.MockTransport(handler), **kw)):
        if stream:
            events = list(providers.stream_completion(model="deepseek:standard:deepseek-flash", system="Test", messages=[]))
            assert "".join(e.text for e in events) == "Answer"
            assert events[-1].completed and events[-1].output_tokens == 9
        else:
            reply = providers.request_completion(model="deepseek:standard:deepseek-flash", system="Test", messages=[])
            assert reply.content == "Answer" and reply.input_tokens == 7


def test_truncated_stream_never_completes(monkeypatch):
    from pydantic import SecretStr
    from app.core.config import get_settings
    monkeypatch.setattr(get_settings(), "deepseek_api_key", SecretStr("test"))
    real_client = httpx.Client
    transport = httpx.MockTransport(lambda _: httpx.Response(200, text='data: {"choices":[{"delta":{"content":"partial"}}]}\n\n'))
    with patch.object(providers.httpx, "Client", side_effect=lambda **kw: real_client(transport=transport, **kw)):
        with pytest.raises(MiniMaxRequestError):
            list(providers.stream_completion(model="deepseek:light:deepseek-flash", system="Test", messages=[]))


def test_ai_duplicate_request_replays_without_provider_or_second_charge(monkeypatch):
    from uuid import uuid4
    from app.models.ai import AiUsageEvent
    from app.services.ai import assistant
    from app.services.ai.minimax import MiniMaxReply
    from sqlalchemy import select, func
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        tenant = Tenant(slug="idem", name="Test")
        db.add(tenant)
        db.flush()
        user = User(tenant_id=tenant.id, username="IDEM_S100", full_name="Test", password_hash="hash")
        db.add(user)
        db.commit()
        conversation = assistant.create_conversation(db, user, topic="academic_planning")
        calls = []
        def complete(**kwargs):
            calls.append(kwargs)
            return MiniMaxReply("Answer", 1, 2)
        monkeypatch.setattr(assistant, "request_completion", complete)
        request_id = uuid4()
        first = assistant.send_message(db, user, conversation, content="Hello", request_id=request_id)
        replay = assistant.send_message(db, user, conversation, content="Hello", request_id=request_id)
        assert first[0].id == replay[0].id and first[1].id == replay[1].id
        assert len(calls) == 1
        assert db.scalar(select(func.count(AiUsageEvent.id))) == 1
        with pytest.raises(assistant.AiAssistantError, match="request_id_conflict"):
            assistant.send_message(db, user, conversation, content="Changed", request_id=request_id)


def test_shared_rate_limits_and_credential_free_audit(monkeypatch):
    from app.services import request_security
    from app.models.security import SecurityAudit
    from sqlalchemy import select
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    monkeypatch.setattr(request_security, "SessionLocal", lambda: Session(engine))
    monkeypatch.setattr(request_security.time, "time", lambda: 12000)
    assert all(request_security.rate_allowed("test-ip", "/auth/login") for _ in range(10))
    assert not request_security.rate_allowed("test-ip", "/auth/login")
    assert request_security.rate_allowed("another-ip", "/auth/login")
    event_id = request_security.begin_audit("bad-token", "POST", "/api/v1/admin/pre-registrations/reissue")
    request_security.finish_audit(event_id, 401)
    with Session(engine) as db:
        event = db.scalar(select(SecurityAudit))
        assert event.status == 401 and event.actor_id is None
        assert not hasattr(event, "body") and not hasattr(event, "token")


def test_latest_minimax_flash_never_disables_thinking(monkeypatch):
    from types import SimpleNamespace
    from app.services.ai import minimax
    captured = []
    class Client:
        def __init__(self):
            self.messages = self
        def create(self, **kwargs):
            captured.append(kwargs)
            return SimpleNamespace(content=[SimpleNamespace(type="text", text="OK")], stop_reason="end_turn", usage=None)
        def close(self):
            pass
    monkeypatch.setattr(minimax, "_client", Client)
    providers.request_completion(model="minimax:light:MiniMax-M3.1-Flash", system="Test", messages=[])
    assert captured[0]["extra_body"] == {"output_config": {"effort": "low"}}
    assert captured[0]["max_tokens"] >= 8192


def test_upload_rejects_disguised_pdf_and_removes_temporary_file(tmp_path, monkeypatch):
    import asyncio
    from fastapi import UploadFile
    from app.core.config import get_settings
    from app.services import resources
    monkeypatch.setattr(get_settings(), "resource_storage_path", str(tmp_path))
    with pytest.raises(resources.ResourceError, match="file_content_mismatch"):
        asyncio.run(resources.stage_upload(UploadFile(filename="fake.pdf", file=BytesIO(b"MZ executable"))))
    assert not list(tmp_path.iterdir())


def test_resources_are_institution_scoped_in_catalog_recommendations_download_and_ai():
    from app.models.user import StudentProfile, MentorProfile
    from app.models.resource import Resource
    from app.services import resources
    from app.services.ai.assistant import _resource_catalog_context
    from app.api.v1.endpoints.resources import download_resource
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        tenant = Tenant(slug="school-scope", name="Test")
        db.add(tenant)
        db.flush()
        student = User(tenant_id=tenant.id, full_name="Student", password_hash="hash")
        same = User(tenant_id=tenant.id, full_name="Same", password_hash="hash")
        other = User(tenant_id=tenant.id, full_name="Other", password_hash="hash")
        db.add_all([student, same, other])
        db.flush()
        db.add_all([StudentProfile(user_id=student.id, institution_abbr="AAA"), MentorProfile(user_id=same.id, institution_abbr="AAA"), MentorProfile(user_id=other.id, institution_abbr="BBB")])
        allowed = Resource(tenant_id=tenant.id, owner_user_id=same.id, resource_type="paper", title="Same-school paper", topics=[], tags=[])
        hidden = Resource(tenant_id=tenant.id, owner_user_id=other.id, resource_type="paper", title="Other-school secret", topics=[], tags=[], file_storage_key="secret.pdf")
        db.add_all([allowed, hidden])
        db.commit()
        assert [r.id for r in resources.list_resources(db, tenant_id=tenant.id, viewer=student)] == [allowed.id]
        assert resources.get_resource(db, tenant_id=tenant.id, resource_id=hidden.id, viewer=student) is None
        assert [r.id for r, _ in resources.recommended_resources(db, student, limit=10)] == [allowed.id]
        catalog = _resource_catalog_context(db, student)
        assert allowed.title in catalog and hidden.title not in catalog
        with pytest.raises(HTTPException) as denied:
            download_resource(hidden.id, student, db)
        assert denied.value.status_code == 404
        student.student_profile.institution_abbr = None
        db.commit()
        assert resources.list_resources(db, tenant_id=tenant.id, viewer=student) == []
