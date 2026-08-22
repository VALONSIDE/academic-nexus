from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models import selection as selection_models  # noqa: F401
from app.models.tenant import Tenant
from app.models.user import MentorProfile, Role, StudentProfile, User
from app.services.selection import mentor_confirm, mentor_invite, student_cancel, student_choose, student_settings, tenant_settings


def _users(db: Session):
    tenant = Tenant(slug="selection-test", name="Selection Test")
    db.add(tenant); db.flush()
    student_role = Role(tenant_id=tenant.id, code="student", name_zh="学生", name_en="Student")
    mentor_role = Role(tenant_id=tenant.id, code="mentor", name_zh="导师", name_en="Mentor")
    student = User(tenant_id=tenant.id, username="TEST_S1", full_name="Student", password_hash="hash")
    mentor = User(tenant_id=tenant.id, username="TEST_T1", full_name="Mentor", password_hash="hash")
    student.roles.append(student_role); mentor.roles.append(mentor_role)
    db.add_all([student_role, mentor_role, student, mentor]); db.flush()
    db.add_all([StudentProfile(user_id=student.id, research_interests=["AI"], skills=["Python"]), MentorProfile(user_id=mentor.id, research_directions=["AI"], representative_papers=[])])
    db.flush()
    return tenant, student, mentor


def test_student_application_needs_manual_confirmation_and_respects_capacity() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        tenant, student, mentor = _users(db)
        settings = tenant_settings(db, tenant.id); settings.default_capacity = 1
        item = student_choose(db, student, mentor.id, "Please consider me")
        assert item.status == "pending_student"
        db.flush()
        confirmed = mentor_confirm(db, mentor, item.id, "Welcome")
        assert confirmed.status == "confirmed"
        assert confirmed.confirmed_at is not None


def test_mentor_invitation_becomes_confirmed_when_student_accepts() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        tenant, student, mentor = _users(db)
        tenant_settings(db, tenant.id)
        invitation = mentor_invite(db, mentor, student.id, "Join my project")
        assert invitation.status == "pending_mentor"
        accepted = student_choose(db, student, mentor.id, None)
        assert accepted.status == "confirmed"
        assert db.scalar(select(selection_models.MentorSelection).where(selection_models.MentorSelection.id == invitation.id)).status == "confirmed"


def test_a_confirmed_student_cannot_consume_another_mentor_capacity() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        tenant, student, mentor = _users(db)
        other = User(tenant_id=tenant.id, username="TEST_T2", full_name="Other Mentor", password_hash="hash")
        role = db.scalar(select(Role).where(Role.code == "mentor"))
        other.roles.append(role)
        db.add(other); db.flush(); db.add(MentorProfile(user_id=other.id, research_directions=["AI"], representative_papers=[])); db.flush()
        tenant_settings(db, tenant.id)
        selection = student_choose(db, student, mentor.id, None)
        mentor_confirm(db, mentor, selection.id, None)
        try:
            mentor_invite(db, other, student.id, None)
        except Exception as error:
            assert getattr(error, "detail", {}).get("code") == "student_already_matched"
        else:
            raise AssertionError("confirmed student must not be inviteable")


def test_student_choice_override_allows_multiple_choices_and_cancels_the_exact_record() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        tenant, student, mentor = _users(db)
        mentor_role = db.scalar(select(Role).where(Role.code == "mentor"))
        other = User(tenant_id=tenant.id, username="TEST_T2", full_name="Other Mentor", password_hash="hash")
        other.roles.append(mentor_role)
        db.add(other); db.flush()
        db.add(MentorProfile(user_id=other.id, research_directions=["AI"], representative_papers=[])); db.flush()
        settings = tenant_settings(db, tenant.id); settings.default_student_choice_limit = 1
        first = student_choose(db, student, mentor.id, None)
        try:
            student_choose(db, student, other.id, None)
        except Exception as error:
            assert getattr(error, "detail", {}).get("code") == "student_choice_limit_reached"
        else:
            raise AssertionError("the global student choice limit must be enforced")
        student_settings(db, student.id).choice_limit = 2
        second = student_choose(db, student, other.id, None)
        student_cancel(db, student, first.id)
        assert first.status == "cancelled"
        assert second.status == "pending_student"
