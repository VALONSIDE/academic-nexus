from datetime import datetime, timedelta, timezone
import asyncio
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import Mock

import jwt
import pytest
from fastapi import HTTPException, UploadFile
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.v1.endpoints.resources import _validate_url
from app.core.config import get_settings
from app.core.security import create_access_token, decode_access_token, verify_password
from app.db.base import Base
from app.models.ai import AiConversation, AiMessage, AiUsageEvent
from app.models.tenant import Tenant
from app.models.user import MentorProfile, Role, StudentProfile, User
from app.services.ai.assistant import _bounded_messages
from app.services.ai.quota import quota_snapshot, release_ai_call, reserve_ai_call
from app.services.resources import ResourceError, course_duration_from_parts
from app.services.selection import student_cancel, student_choose, tenant_settings
from app.services.subscriptions import refresh_subscription


@pytest.fixture
def account_db():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    # Match the production session: no automatic flush or commit expiration.
    with Session(engine, autoflush=False, expire_on_commit=False) as db:
        tenant = Tenant(slug="review", name="Review")
        db.add(tenant)
        db.flush()
        user = User(tenant_id=tenant.id, username="REVIEW_S1", full_name="Review", password_hash="hash")
        db.add(user)
        db.commit()
        yield db, user
    engine.dispose()


def test_registration_token_cannot_authenticate_an_active_account(account_db):
    db, user = account_db
    token = create_access_token(subject=str(user.id), roles=[], scope="profile_completion")
    with pytest.raises(HTTPException) as error:
        get_current_user(HTTPAuthorizationCredentials(scheme="Bearer", credentials=token), db)
    assert error.value.status_code == 401


@pytest.mark.parametrize("claim", ["sub", "exp", "iat", "scope", "auth_version"])
def test_signed_tokens_must_contain_required_claims(claim):
    payload = decode_access_token(create_access_token(subject="user-id", roles=[]))
    payload.pop(claim)
    assert decode_access_token(jwt.encode(payload, get_settings().jwt_secret_key, algorithm="HS256")) is None


def test_dummy_password_never_authenticates():
    assert not verify_password("AcademicNexus-not-a-valid-password", None)


@pytest.mark.parametrize("budget, expected", [(8, ["old", "hello"]), (5, ["hello"]), (3, ["llo"]), (0, [])])
def test_context_budget_keeps_latest_messages(account_db, monkeypatch, budget, expected):
    db, user = account_db
    monkeypatch.setattr(get_settings(), "ai_context_character_limit", budget)
    conversation = AiConversation(tenant_id=user.tenant_id, user_id=user.id, topic="academic_planning", title="Test")
    db.add(conversation)
    db.flush()
    now = datetime.now(timezone.utc)
    db.add_all([
        AiMessage(conversation_id=conversation.id, role="assistant", content="old", created_at=now - timedelta(seconds=1)),
        AiMessage(conversation_id=conversation.id, role="user", content="hello", created_at=now),
    ])
    db.commit()
    result = _bounded_messages(db, conversation)
    contents = [item["content"][0]["text"] for item in result]
    assert contents == expected
    assert sum(map(len, contents)) <= budget


def test_cancelled_application_cannot_bypass_choice_limit(account_db):
    db, student = account_db
    role = Role(tenant_id=student.tenant_id, code="mentor", name_zh="导师", name_en="Mentor")
    mentors = [User(tenant_id=student.tenant_id, username=f"REVIEW_T{i}", full_name="Mentor", password_hash="hash", roles=[role]) for i in range(2)]
    db.add_all(mentors)
    db.flush()
    db.add(StudentProfile(user_id=student.id, institution_abbr="TEST"))
    db.add_all([MentorProfile(user_id=mentor.id, institution_abbr="TEST") for mentor in mentors])
    tenant_settings(db, student.tenant_id).default_student_choice_limit = 1
    db.commit()
    first = student_choose(db, student, mentors[0].id, None)
    db.commit()
    student_cancel(db, student, first.id)
    db.commit()
    student_choose(db, student, mentors[1].id, None)
    db.commit()
    with pytest.raises(HTTPException) as error:
        student_choose(db, student, mentors[0].id, None)
    assert error.value.detail["code"] == "student_choice_limit_reached"


def test_stale_event_cannot_be_refunded_twice(account_db):
    db, user = account_db
    conversation = AiConversation(tenant_id=user.tenant_id, user_id=user.id, topic="academic_planning", title="Test")
    db.add(conversation)
    db.commit()
    first = reserve_ai_call(db, user, conversation.id)
    reserve_ai_call(db, user, conversation.id)
    with Session(db.get_bind(), expire_on_commit=False) as other:
        cached = other.get(AiUsageEvent, first.id)
        release_ai_call(db, first.id, error_code="failed")
        assert cached.status == "reserved"
        release_ai_call(other, first.id, error_code="failed")
    assert quota_snapshot(db, user.id).credit_balance == 9


def test_refund_from_previous_cycle_does_not_credit_new_cycle(account_db):
    db, user = account_db
    conversation = AiConversation(tenant_id=user.tenant_id, user_id=user.id, topic="academic_planning", title="Test")
    db.add(conversation)
    db.commit()
    event = reserve_ai_call(db, user, conversation.id)
    subscription = refresh_subscription(db, user)
    old_time = datetime.now(timezone.utc) - timedelta(days=40)
    event.created_at = old_time
    subscription.cycle_started_at = old_time
    subscription.cycle_ends_at = old_time + timedelta(days=30)
    db.commit()
    reserve_ai_call(db, user, conversation.id)
    release_ai_call(db, event.id, error_code="failed")
    assert quota_snapshot(db, user.id).credit_balance == 9


@pytest.mark.parametrize("value", ["https://", "javascript:alert(1)", "https://user:password@example.com"])
def test_resource_url_rejects_invalid_or_credentialed_links(value):
    with pytest.raises(HTTPException):
        _validate_url(value)


@pytest.mark.parametrize("hours, minutes", [("10000", "0"), ("1", "100")])
def test_duration_does_not_silently_truncate_numbers(hours, minutes):
    with pytest.raises(ResourceError):
        course_duration_from_parts(hours, minutes)


@pytest.mark.parametrize("role_code, profile_type", [("student", StudentProfile), ("mentor", MentorProfile)])
def test_managed_user_response_contains_contact_once(account_db, role_code, profile_type):
    from app.api.v1.endpoints.users import serialize_managed_user

    db, user = account_db
    user.roles.append(Role(tenant_id=user.tenant_id, code=role_code, name_zh="角色", name_en="Role"))
    user.phone = "+8613800138000"
    db.add(profile_type(user_id=user.id))
    db.commit()
    result = serialize_managed_user(user)
    assert result.phone == user.phone
    assert result.role == role_code


def test_bootstrap_never_promotes_an_ordinary_account_by_email(account_db, monkeypatch):
    from app.services import bootstrap

    db, user = account_db
    tenant = db.get(Tenant, user.tenant_id)
    tenant.slug = get_settings().default_tenant_slug
    user.email = get_settings().initial_admin_email
    db.commit()
    monkeypatch.setattr(bootstrap, "SessionLocal", lambda: Session(db.get_bind()))
    with pytest.raises(RuntimeError, match="refusing to grant privileges"):
        bootstrap.ensure_bootstrap_data()
    db.expire_all()
    assert user.roles == []


def test_cross_institution_selection_is_rejected(account_db):
    db, student = account_db
    mentor = User(tenant_id=student.tenant_id, username="OTHER_T1", full_name="Other Mentor", password_hash="hash",
                  roles=[Role(tenant_id=student.tenant_id, code="mentor", name_zh="导师", name_en="Mentor")])
    db.add(mentor)
    db.flush()
    db.add_all([StudentProfile(user_id=student.id, institution_abbr="ONE"), MentorProfile(user_id=mentor.id, institution_abbr="TWO")])
    db.commit()
    with pytest.raises(HTTPException) as error:
        student_choose(db, student, mentor.id, None)
    assert error.value.status_code == 403


@pytest.mark.parametrize("disconnect", [True, False])
def test_incomplete_ai_stream_refunds_and_removes_the_turn(account_db, monkeypatch, disconnect):
    from app.services.ai import assistant

    db, user = account_db
    conversation = assistant.create_conversation(db, user, topic="academic_planning")
    monkeypatch.setattr(assistant, "stream_completion", lambda **kwargs: iter([SimpleNamespace(text="partial", completed=False)]))
    stream = assistant.stream_message(db, user, conversation, content="Help me")
    assert next(stream).text == "partial"
    if disconnect:
        stream.close()
    else:
        with pytest.raises(assistant.AiAssistantError):
            next(stream)
    assert quota_snapshot(db, user.id).credit_balance == 10
    assert assistant.list_messages(db, conversation) == []


def test_resource_response_failure_does_not_delete_committed_file(account_db, tmp_path, monkeypatch):
    from app.api.v1.endpoints import resources
    from app.models.resource import Resource
    from app.services import resources as service

    db, mentor = account_db
    monkeypatch.setattr(get_settings(), "resource_storage_path", str(tmp_path))
    monkeypatch.setattr(resources, "_serialize", Mock(side_effect=RuntimeError("response failed")))
    upload = UploadFile(filename="paper.pdf", file=BytesIO(b"test attachment"))
    with pytest.raises(RuntimeError, match="response failed"):
        asyncio.run(resources.create_resource(resource_type="paper", title="Test paper", db=db, mentor=mentor, file=upload))
    resource = db.scalar(select(Resource))
    assert resource is not None
    assert service.file_path(resource).read_bytes() == b"test attachment"
    assert upload.file.closed


def test_failed_resource_deletion_keeps_the_file(account_db, tmp_path, monkeypatch):
    from app.api.v1.endpoints import resources
    from app.services import resources as service
    from app.models.resource import Resource

    db, mentor = account_db
    monkeypatch.setattr(get_settings(), "resource_storage_path", str(tmp_path))
    result = asyncio.run(resources.create_resource(resource_type="paper", title="Test paper", db=db, mentor=mentor,
                         file=UploadFile(filename="paper.pdf", file=BytesIO(b"keep me"))))
    resource = db.get(Resource, result.id)
    path = service.file_path(resource)
    monkeypatch.setattr(db, "commit", Mock(side_effect=RuntimeError("commit failed")))
    with pytest.raises(RuntimeError, match="commit failed"):
        resources.delete_resource(resource.id, db, mentor)
    db.rollback()
    assert path.read_bytes() == b"keep me"
    assert db.get(Resource, result.id) is not None


def test_rejected_upload_is_closed():
    from app.services.resources import stage_upload

    upload = UploadFile(filename="payload.exe", file=BytesIO(b"test"))
    with pytest.raises(ResourceError):
        asyncio.run(stage_upload(upload))
    assert upload.file.closed


def test_import_row_limit_and_workbook_cleanup(monkeypatch):
    from app.services import pre_registration_import as importer
    from openpyxl import Workbook

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = importer.TEMPLATE_SHEET
    sheet.append(importer.TEMPLATE_HEADERS)
    for index in range(2):
        sheet.append(["TEST", "测试大学", "测试学院", "student", "测试学生", f"S{index}"])
    data = BytesIO()
    workbook.save(data)
    monkeypatch.setattr(importer, "MAX_IMPORT_ROWS", 1)
    with pytest.raises(importer.PreRegistrationImportError, match="Import row limit exceeded"):
        importer.parse_import_workbook(data.getvalue())


def test_health_check_fails_when_database_is_unavailable():
    from app.main import health_check
    from sqlalchemy.exc import OperationalError

    db = Mock()
    db.execute.side_effect = OperationalError("SELECT 1", {}, Exception("unavailable"))
    with pytest.raises(HTTPException) as error:
        health_check(db)
    assert error.value.status_code == 503
