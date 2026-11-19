import asyncio
from datetime import datetime, timezone

import httpx
import pytest
from fastapi import FastAPI, HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.v1.endpoints.auth import update_contact
from app.api.v1.endpoints.notifications import ReminderRequest, admin_router, inbox, read_one, remind
from app.api.v1.endpoints.resources import update_resource_quotas
from app.api.v1.endpoints.selection import update_mentor_settings, update_selection_user
from app.api.v1.endpoints.users import update_managed_user
from app.db.base import Base
from app.db.session import get_db
from app.models.ai import AiMessage, AiUserQuota
from app.models.subscription import InstitutionAdminScope, InstitutionSubscriptionAllocation
from app.models.tenant import Tenant
from app.models.user import MentorProfile, Role, StudentProfile, User
from app.models.workspace import WorkspaceEvent
from app.schemas.auth import ContactUpdateRequest
from app.schemas.profiles import AdminUserUpdateRequest
from app.schemas.resource import AdminResourceQuotaBatchRequest
from app.schemas.selection import AdminSelectionUserUpdate, MentorSelectionSettingsUpdate
from app.services.ai.assistant import create_conversation
from app.services.ai.selection_cards import execute_card, proposed_card
from app.services.resources import MEGABYTE, quota_snapshot, reserve_file_bytes
from app.services.selection import mentor_confirm
from app.services.subscription_reporting import history, inventory
from app.services.subscriptions import activate_subscription_key, issue_subscription_keys, revoke_subscription_key


@pytest.fixture
def workspace():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        tenant = Tenant(slug="workspace", name="Workspace")
        db.add(tenant)
        db.flush()
        roles = {code: Role(tenant_id=tenant.id, code=code, name_zh=code, name_en=code)
                 for code in ("student", "mentor", "institution_admin", "super_admin")}
        db.add_all(roles.values())
        users = {}
        for username, school, code, extra in (
            ("student_a", "AAA", "student", None),
            ("mentor_a", "AAA", "mentor", None),
            ("mentor_b", "BBB", "mentor", None),
            ("school_admin", "AAA", "mentor", "institution_admin"),
            ("super", None, "super_admin", None),
        ):
            user = User(tenant_id=tenant.id, full_name=username, username=username, password_hash="hash",
                        email=f"{username}@example.edu", wechat=username, roles=[roles[code]])
            if extra:
                user.roles.append(roles[extra])
            db.add(user)
            db.flush()
            if school:
                profile = StudentProfile if code == "student" else MentorProfile
                db.add(profile(user_id=user.id, institution_abbr=school, department="Science",
                               profile_completed_at=datetime.now(timezone.utc)))
            users[username] = user
        db.add(InstitutionAdminScope(tenant_id=tenant.id, user_id=users["school_admin"].id,
                                    institution_abbr="AAA", institution_name_zh="AAA"))
        db.commit()
        yield db, users


def test_card_requires_current_school_state_and_executes_once(workspace):
    db, users = workspace
    student, mentor, other = (users[key] for key in ("student_a", "mentor_a", "mentor_b"))
    assert proposed_card(db, student, other.id, "apply") is None
    conversation = create_conversation(db, student, topic="selection_advisor")
    card = proposed_card(db, student, mentor.id, "apply")
    message = AiMessage(conversation_id=conversation.id, role="assistant", content="Suggestion", action_card=card)
    db.add(message)
    db.commit()
    applied = execute_card(db, student, conversation, message.id)
    assert execute_card(db, student, conversation, message.id) == applied
    events = db.scalars(select(WorkspaceEvent).where(WorkspaceEvent.kind == "selection_applied")).all()
    assert len(events) == 1 and events[0].recipient_id == mentor.id
    with pytest.raises(HTTPException) as forbidden:
        read_one(events[0].id, db, other)
    assert forbidden.value.status_code == 404
    read_one(events[0].id, db, mentor)
    assert inbox(db, mentor, limit=20, offset=0)["unread"] == 0
    from uuid import UUID
    mentor_confirm(db, mentor, UUID(applied["selection_id"]), None)
    db.commit()
    assert inbox(db, student, limit=20, offset=0)["items"][0]["kind"] == "selection_confirmed"


def test_scoped_reminders_and_admin_contact_rules(workspace):
    db, users = workspace
    student, admin, school_admin = (users[key] for key in ("student_a", "super", "school_admin"))
    reminder = ReminderRequest(institution="AAA", recipient_id=school_admin.id, category="quota")
    assert remind(reminder, db, admin) == remind(reminder, db, admin)
    assert inbox(db, school_admin, limit=20, offset=0)["unread"] == 1
    with pytest.raises(HTTPException):
        remind(ReminderRequest(institution="BBB", recipient_id=school_admin.id, category="quota"), db, school_admin)
    with pytest.raises(HTTPException):
        update_contact(ContactUpdateRequest(email="changed@example.edu"), school_admin, db)
    with pytest.raises(HTTPException):
        update_managed_user(school_admin.id, AdminUserUpdateRequest(wechat="changed"), db, admin)
    result = update_managed_user(student.id, AdminUserUpdateRequest(wechat="changed", phone="+8613800138000"), db, admin)
    assert result.wechat == "changed" and result.phone == "+8613800138000"


def test_institution_admin_cannot_list_reminder_recipients_or_send_in_own_school(workspace):
    _, users = workspace
    school_admin = users["school_admin"]
    assert {role.code for role in school_admin.roles} == {"mentor", "institution_admin"}
    app = FastAPI()
    app.include_router(admin_router)
    app.dependency_overrides[get_db] = lambda: None
    app.dependency_overrides[get_current_user] = lambda: school_admin
    async def request_as_institution_admin():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            recipients = await client.get("/admin/notifications/recipients", params={"institution": "AAA"})
            reminder = await client.post("/admin/notifications/reminders", json={
                "institution": "AAA", "recipient_id": str(school_admin.id), "category": "delivery",
            })
        assert recipients.status_code == reminder.status_code == 403

    asyncio.run(request_as_institution_admin())


def test_inventory_counts_and_history_are_per_school(workspace):
    db, users = workspace
    admin, student = users["super"], users["student_a"]
    db.add(InstitutionSubscriptionAllocation(tenant_id=admin.tenant_id, institution_abbr="AAA",
                                             institution_name_zh="AAA", pro_credits=4))
    db.commit()
    first, second, _ = issue_subscription_keys(db, admin, institution_abbr="AAA", plan_code="pro", quantity=3)
    activate_subscription_key(db, student, raw_key=first.plaintext)
    revoke_subscription_key(db, admin, second.key.id)
    quota = db.scalar(select(AiUserQuota).where(AiUserQuota.user_id == student.id))
    quota.credit_balance = 0
    db.commit()
    pro = inventory(db, admin.tenant_id, "AAA")[0]
    assert (pro["available"], pro["total_issued"], pro["issued"], pro["exhausted"], pro["reclaimed"]) == (2, 3, 1, 1, 1)
    assert not any(item["total_issued"] for item in inventory(db, admin.tenant_id, "BBB"))
    records = history(db, admin.tenant_id, "AAA", 20, 0)["items"]
    assert len(records) == 5
    assert {row["kind"] for row in records} == {"subscription_issued", "subscription_activated", "subscription_reclaimed"}


def test_quota_batches_roll_back_and_selection_exceptions_are_scoped(workspace):
    db, users = workspace
    admin, school_admin, mentor, other = (users[key] for key in ("super", "school_admin", "mentor_a", "mentor_b"))
    before = quota_snapshot(db, mentor.id).quota_bytes
    reserve_file_bytes(db, other.id, 5 * MEGABYTE)
    db.commit()
    with pytest.raises(HTTPException):
        update_resource_quotas(AdminResourceQuotaBatchRequest(user_ids=[mentor.id, other.id], quota_mb=1), db, admin)
    assert quota_snapshot(db, mentor.id).quota_bytes == before
    with pytest.raises(HTTPException):
        update_selection_user(other.id, AdminSelectionUserUpdate(capacity=3), db, school_admin)
    result = update_selection_user(
        mentor.id, AdminSelectionUserUpdate(capacity=3, is_exempt=True, selection_mode="first_come"), db, school_admin,
    )
    assert result.effective_limit == 3 and result.available is None
    with pytest.raises(HTTPException) as forbidden:
        update_mentor_settings(MentorSelectionSettingsUpdate(capacity=200, selection_mode="manual"), db, mentor)
    assert forbidden.value.status_code == 403
    db.rollback()
    result = update_selection_user(mentor.id, AdminSelectionUserUpdate(capacity=None), db, school_admin)
    assert result.capacity is None and result.effective_limit == result.default_limit
    assert result.is_exempt and result.selection_mode == "first_come"
