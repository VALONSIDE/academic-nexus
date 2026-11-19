import pytest
from pydantic import ValidationError
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.db.base import Base
from app.models.user import User, Role, StudentProfile, MentorProfile
from app.models.tenant import Tenant
from app.schemas.profiles import StudentRegistrationCompleteRequest, MentorRegistrationCompleteRequest
from app.schemas.auth import ContactUpdateRequest
from app.api.v1.endpoints.auth import update_contact
from app.services.contacts import load_contact, visible_contact, draft_context, redact_unshared


@pytest.fixture
def contacts():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        tenant = Tenant(slug='contacts', name='School')
        db.add(tenant)
        db.flush()
        roles = [Role(tenant_id=tenant.id, code=code, name_zh=code, name_en=code) for code in ('student', 'mentor')]
        db.add_all(roles)
        viewer = User(tenant_id=tenant.id, username='AAA_S100', full_name='Student', password_hash='hash', email='student@example.edu', wechat='student_wechat')
        target = User(tenant_id=tenant.id, username='AAA_T100', full_name='Mentor', password_hash='hash', email='mentor@example.edu', phone='+8613800138000', wechat='mentor_wechat')
        other = User(tenant_id=tenant.id, username='BBB_T100', full_name='Other', password_hash='hash', email='other@example.edu')
        viewer.roles = [roles[0]]
        target.roles = other.roles = [roles[1]]
        db.add_all([viewer, target, other])
        db.flush()
        db.add_all([StudentProfile(user_id=viewer.id, institution_abbr='AAA'), MentorProfile(user_id=target.id, institution_abbr='AAA'), MentorProfile(user_id=other.id, institution_abbr='BBB')])
        db.commit()
        yield db, viewer, target, other


def test_contacts_default_private_and_cannot_cross_school(contacts):
    db, viewer, target, other = contacts
    data = visible_contact(viewer, load_contact(db, viewer, target.id))
    assert all(data[field] is None for field in ('email', 'phone', 'wechat'))
    for channel in ('email', 'sms', 'wechat'):
        with pytest.raises(HTTPException) as hidden:
            draft_context(db, viewer, target.id, channel)
        assert hidden.value.status_code == 403
    other.share_email = True
    db.commit()
    with pytest.raises(HTTPException) as denied:
        load_contact(db, viewer, other.id)
    assert denied.value.status_code == 404
    assert visible_contact(viewer, other)['email'] is None


def test_per_channel_visibility_and_ai_redaction_after_revocation(contacts):
    db, viewer, target, other = contacts
    target.share_email = True
    db.commit()
    assert target.email in draft_context(db, viewer, target.id, 'email')
    assert visible_contact(viewer, target)['phone'] is None
    assert target.email in redact_unshared(db, viewer, [target.email])[0]
    update_contact(ContactUpdateRequest(share_email=False), target, db)
    assert visible_contact(viewer, target)['email'] is None
    with pytest.raises(HTTPException):
        draft_context(db, viewer, target.id, 'email')
    text = redact_unshared(db, viewer, [f'{target.email} {target.phone} {target.wechat} {other.email} {viewer.email}'])[0]
    assert all(value not in text for value in (target.email, target.phone, target.wechat, other.email, viewer.email))
    assert '+86 138 0013 8000' not in redact_unshared(db, viewer, ['+86 138 0013 8000'])[0]


def test_required_contact_cannot_be_cleared_and_flags_cannot_be_null(contacts):
    db, viewer, _, _ = contacts
    for payload in ({'email': ''}, {'wechat': ''}, {'share_email': None}):
        with pytest.raises(HTTPException):
            update_contact(ContactUpdateRequest(**payload), viewer, db)
    assert viewer.email == 'student@example.edu'
    assert viewer.wechat == 'student_wechat'


@pytest.mark.parametrize('kind', ['student', 'mentor'])
def test_registration_requires_real_format_email_and_wechat(kind):
    if kind == 'student':
        schema = StudentRegistrationCompleteRequest
        payload = dict(research_interests=['AI'], skills=['Python'], academic_performance='Good', academic_goals='Research', research_experience='Project')
    else:
        schema = MentorRegistrationCompleteRequest
        payload = dict(research_directions=['AI'], representative_papers=['Paper'], research_projects='Project', mentoring_style='Regular meetings')
    for extra in ({}, {'email': 'bad', 'wechat': 'test_user'}, {'email': 'user@example.edu', 'wechat': ''}):
        with pytest.raises(ValidationError):
            schema(**payload, **extra)
    result = schema(**payload, email='USER@example.edu', wechat='test_user')
    assert result.email == 'user@example.edu'
    assert not result.share_email and not result.share_phone and not result.share_wechat


def test_ai_does_not_invoke_provider_for_hidden_or_cross_school_contact(contacts, monkeypatch):
    from app.services.ai import assistant
    db, viewer, target, other = contacts
    calls = []
    monkeypatch.setattr(assistant, 'request_completion', lambda **kw: calls.append(kw))
    conversation = assistant.create_conversation(db, viewer, topic='mentor_consultation')
    for user in (target, other):
        with pytest.raises(HTTPException):
            assistant.send_message(db, viewer, conversation, content='Draft an email', contact_user_id=user.id, contact_channel='email')
    assert not calls


def test_template_example_has_single_role_prefix():
    from io import BytesIO
    from openpyxl import load_workbook
    from app.services.pre_registration_import import build_import_template
    book = load_workbook(BytesIO(build_import_template()))
    example = book['填写示例 Examples']
    assert example['F3'].value == '10086'
    assert example['G3'].value == 'CUC_T10086'
    book.close()


def test_dashboard_counts_only_same_school_candidates_and_resources(contacts):
    from datetime import datetime, timezone
    from app.models.resource import Resource
    from app.api.v1.endpoints.dashboard import read_dashboard
    db, viewer, target, other = contacts
    target.mentor_profile.profile_completed_at = other.mentor_profile.profile_completed_at = datetime.now(timezone.utc)
    db.add_all([Resource(tenant_id=viewer.tenant_id, owner_user_id=target.id, title='School resource', resource_type='paper', topics=[], tags=[]), Resource(tenant_id=viewer.tenant_id, owner_user_id=other.id, title='Other resource', resource_type='paper', topics=[], tags=[])])
    db.commit()
    result = read_dashboard(viewer, db)
    metrics = {item.code: item.value for item in result.metrics}
    assert metrics['mentor_matches_available'] == 1
    assert metrics['resources_total'] == 1


def test_actual_provider_payload_normalizes_text_blocks_and_redacts_hidden_history(contacts):
    from app.services.ai.assistant import create_conversation, _provider_payload
    from app.models.ai import AiMessage
    db, viewer, target, _ = contacts
    conversation = create_conversation(db, viewer, topic='academic_planning')
    db.add(AiMessage(conversation_id=conversation.id, role='user', content=f'Draft a message to {target.email} at {target.phone} or {target.wechat}'))
    db.commit()
    system, messages = _provider_payload(db, viewer, conversation, '')
    assert isinstance(system, str)
    assert isinstance(messages[0]['content'], str)
    assert target.email not in messages[0]['content']
    assert target.phone not in messages[0]['content']
    assert target.wechat not in messages[0]['content']


def test_unexpected_prompt_failure_refunds_application_credit(contacts, monkeypatch):
    from app.services.ai import assistant
    from app.services.ai.quota import quota_snapshot
    db, viewer, _, _ = contacts
    conversation = assistant.create_conversation(db, viewer, topic='academic_planning')
    before = quota_snapshot(db, viewer.id).credit_balance
    def fail(*args):
        raise RuntimeError('synthetic prompt preparation failure')
    monkeypatch.setattr(assistant, '_provider_payload', fail)
    with pytest.raises(assistant.AiAssistantError):
        assistant.send_message(db, viewer, conversation, content='Test')
    assert quota_snapshot(db, viewer.id).credit_balance == before


def test_legacy_account_must_complete_contact_before_using_business_api(contacts):
    from starlette.requests import Request
    from fastapi.security import HTTPAuthorizationCredentials
    from app.api.deps import get_current_user
    from app.core.security import create_access_token
    db, viewer, _, _ = contacts
    viewer.wechat = None
    db.commit()
    token = create_access_token(subject=str(viewer.id), roles=['student'], auth_version=viewer.auth_version)
    credentials = HTTPAuthorizationCredentials(scheme='Bearer', credentials=token)
    def request(path):
        return Request({'type': 'http', 'method': 'GET', 'path': path, 'headers': [], 'scheme': 'http', 'server': ('testserver', 80), 'query_string': b''})
    with pytest.raises(HTTPException) as blocked:
        get_current_user(credentials, db, request('/api/v1/ai/quota'))
    assert blocked.value.detail['code'] == 'contact_profile_required'
    assert get_current_user(credentials, db, request('/api/v1/auth/me')).id == viewer.id
    update_contact(ContactUpdateRequest(wechat='completed_wechat'), viewer, db)
    assert get_current_user(credentials, db, request('/api/v1/ai/quota')).id == viewer.id
