"""Transactional state machine for the student--mentor mutual-selection workflow."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.models.selection import MentorSelection, MentorSelectionSetting, SelectionSettings, StudentSelectionSetting
from app.models.user import User
from app.services.admin_scope import user_institution_abbr

ACTIVE = ("pending_student", "pending_mentor")


def _error(code: str, http_status: int = status.HTTP_409_CONFLICT) -> None:
    raise HTTPException(status_code=http_status, detail={"code": code})


def tenant_settings(db: Session, tenant_id: UUID, *, lock: bool = False) -> SelectionSettings:
    statement = select(SelectionSettings).where(SelectionSettings.tenant_id == tenant_id)
    if lock:
        db.flush()
        statement = statement.with_for_update().execution_options(populate_existing=True)
    item = db.scalar(statement)
    if item is None:
        if db.get_bind().dialect.name == "postgresql":
            db.execute(pg_insert(SelectionSettings).values(tenant_id=tenant_id).on_conflict_do_nothing(index_elements=["tenant_id"]))
            return db.scalars(statement).one()
        item = SelectionSettings(tenant_id=tenant_id)
        db.add(item)
        db.flush()
    return item


def mentor_settings(db: Session, mentor_id: UUID, default_capacity: int, *, lock: bool = False) -> MentorSelectionSetting:
    statement = select(MentorSelectionSetting).where(MentorSelectionSetting.mentor_user_id == mentor_id)
    if lock:
        db.flush()
        statement = statement.with_for_update().execution_options(populate_existing=True)
    item = db.scalar(statement)
    if item is None:
        if db.get_bind().dialect.name == "postgresql":
            db.execute(pg_insert(MentorSelectionSetting).values(mentor_user_id=mentor_id).on_conflict_do_nothing(index_elements=["mentor_user_id"]))
            return db.scalars(statement).one()
        item = MentorSelectionSetting(mentor_user_id=mentor_id)
        db.add(item)
        db.flush()
    return item


def student_settings(db: Session, student_id: UUID, *, lock: bool = False) -> StudentSelectionSetting:
    statement = select(StudentSelectionSetting).where(StudentSelectionSetting.student_user_id == student_id)
    if lock:
        db.flush()
        statement = statement.with_for_update().execution_options(populate_existing=True)
    item = db.scalar(statement)
    if item is None:
        if db.get_bind().dialect.name == "postgresql":
            db.execute(pg_insert(StudentSelectionSetting).values(student_user_id=student_id).on_conflict_do_nothing(index_elements=["student_user_id"]))
            return db.scalars(statement).one()
        item = StudentSelectionSetting(student_user_id=student_id)
        db.add(item)
        db.flush()
    return item


def capacity_of(item: MentorSelectionSetting, default_capacity: int) -> int:
    return item.capacity if item.capacity is not None else default_capacity


def capacity_counts(db: Session, mentor_id: UUID) -> tuple[int, int]:
    confirmed = db.scalar(select(func.count()).select_from(MentorSelection).where(MentorSelection.mentor_user_id == mentor_id, MentorSelection.status == "confirmed")) or 0
    invitations = db.scalar(select(func.count()).select_from(MentorSelection).where(MentorSelection.mentor_user_id == mentor_id, MentorSelection.status == "pending_mentor")) or 0
    return int(confirmed), int(invitations)


def _ensure_open(db: Session, tenant_id: UUID) -> SelectionSettings:
    settings = tenant_settings(db, tenant_id, lock=True)
    if not settings.is_open:
        _error("selection_closed")
    return settings


def _get_role_user(db: Session, user_id: UUID, tenant_id: UUID, role: str, *, lock: bool = False) -> User:
    statement = select(User).where(User.id == user_id, User.tenant_id == tenant_id, User.is_active.is_(True), User.roles.any(code=role))
    if lock:
        statement = statement.with_for_update()
    user = db.scalar(statement)
    if user is None:
        _error(f"{role}_not_found", status.HTTP_404_NOT_FOUND)
    return user


def _reserve_available(db: Session, mentor_id: UUID, setting: MentorSelectionSetting, default_capacity: int) -> None:
    if setting.is_exempt:
        return
    confirmed, invitations = capacity_counts(db, mentor_id)
    if confirmed + invitations >= capacity_of(setting, default_capacity):
        _error("mentor_capacity_full")


def _assert_student_choice_available(db: Session, student_id: UUID, settings: SelectionSettings) -> StudentSelectionSetting:
    item = student_settings(db, student_id, lock=True)
    if item.is_exempt:
        return item
    limit = item.choice_limit if item.choice_limit is not None else settings.default_student_choice_limit
    used = db.scalar(select(func.count()).select_from(MentorSelection).where(MentorSelection.student_user_id == student_id, MentorSelection.status == "pending_student")) or 0
    if int(used) >= limit:
        _error("student_choice_limit_reached")
    return item


def _confirm(db: Session, selection: MentorSelection) -> MentorSelection:
    """Confirm one pair and close all the student's other active choices atomically."""
    # Serialize all confirmations for the same student.  Locking only mentor
    # capacity would still allow two different mentors to confirm concurrently.
    db.scalar(select(User.id).where(User.id == selection.student_user_id).with_for_update())
    other_confirmed = db.scalar(
        select(MentorSelection.id).where(
            MentorSelection.student_user_id == selection.student_user_id,
            MentorSelection.id != selection.id,
            MentorSelection.status == "confirmed",
        )
    )
    if other_confirmed is not None:
        _error("student_already_matched")
    db.execute(
        update(MentorSelection)
        .where(MentorSelection.student_user_id == selection.student_user_id, MentorSelection.id != selection.id, MentorSelection.status.in_(ACTIVE))
        .values(status="cancelled")
    )
    selection.status = "confirmed"
    selection.confirmed_at = datetime.now(timezone.utc)
    return selection


def student_choose(db: Session, student: User, mentor_id: UUID, note: str | None) -> MentorSelection:
    settings = _ensure_open(db, student.tenant_id)
    mentor = _get_role_user(db, mentor_id, student.tenant_id, "mentor", lock=True)
    if not user_institution_abbr(student) or user_institution_abbr(student) != user_institution_abbr(mentor):
        _error("institution_scope_forbidden", status.HTTP_403_FORBIDDEN)
    mentor_setting = mentor_settings(db, mentor_id, settings.default_capacity, lock=True)
    existing = db.scalar(select(MentorSelection).where(MentorSelection.student_user_id == student.id, MentorSelection.mentor_user_id == mentor_id).with_for_update())
    confirmed_existing = db.scalar(select(MentorSelection.id).where(MentorSelection.student_user_id == student.id, MentorSelection.status == "confirmed").with_for_update())
    if confirmed_existing and (existing is None or existing.id != confirmed_existing):
        _error("student_already_matched")
    if existing and existing.status == "confirmed":
        _error("already_confirmed")
    if existing and existing.status == "pending_mentor":
        return _confirm(db, existing)
    if existing is None or existing.status != "pending_student":
        _assert_student_choice_available(db, student.id, settings)
    if mentor_setting.selection_mode == "first_come":
        _reserve_available(db, mentor_id, mentor_setting, settings.default_capacity)
        if existing is None:
            existing = MentorSelection(tenant_id=student.tenant_id, student_user_id=student.id, mentor_user_id=mentor_id, status="pending_student", student_note=note)
            db.add(existing)
            db.flush()
        else:
            existing.status, existing.student_note = "pending_student", note
        return _confirm(db, existing)
    if existing is None:
        existing = MentorSelection(tenant_id=student.tenant_id, student_user_id=student.id, mentor_user_id=mentor_id, status="pending_student", student_note=note)
        db.add(existing)
        db.flush()
    else:
        existing.status, existing.student_note = "pending_student", note
    student_setting = student_settings(db, student.id)
    limit = student_setting.choice_limit if student_setting.choice_limit is not None else settings.default_student_choice_limit
    if not student_setting.is_exempt and limit == 1:
        db.execute(update(MentorSelection).where(MentorSelection.student_user_id == student.id, MentorSelection.id != existing.id, MentorSelection.status == "pending_student").values(status="cancelled"))
    return existing


def student_cancel(db: Session, student: User, selection_id: UUID | None = None) -> None:
    _ensure_open(db, student.tenant_id)
    statement = select(MentorSelection).where(
        MentorSelection.student_user_id == student.id,
        MentorSelection.status.in_(("pending_student", "pending_mentor")),
    )
    if selection_id is not None:
        statement = statement.where(MentorSelection.id == selection_id)
    item = db.scalar(statement.order_by(MentorSelection.updated_at.desc()).with_for_update())
    if item is None:
        _error("no_pending_choice", status.HTTP_404_NOT_FOUND)
    item.status = "cancelled"


def mentor_invite(db: Session, mentor: User, student_id: UUID, note: str | None) -> MentorSelection:
    settings = _ensure_open(db, mentor.tenant_id)
    student = _get_role_user(db, student_id, mentor.tenant_id, "student", lock=True)
    if not user_institution_abbr(mentor) or user_institution_abbr(mentor) != user_institution_abbr(student):
        _error("institution_scope_forbidden", status.HTTP_403_FORBIDDEN)
    if db.scalar(select(MentorSelection.id).where(MentorSelection.student_user_id == student_id, MentorSelection.status == "confirmed").with_for_update()):
        _error("student_already_matched")
    mentor_setting = mentor_settings(db, mentor.id, settings.default_capacity, lock=True)
    existing = db.scalar(select(MentorSelection).where(MentorSelection.student_user_id == student_id, MentorSelection.mentor_user_id == mentor.id).with_for_update())
    if existing and existing.status == "confirmed":
        _error("already_confirmed")
    if existing is None or existing.status != "pending_mentor":
        _reserve_available(db, mentor.id, mentor_setting, settings.default_capacity)
    if existing is None:
        existing = MentorSelection(tenant_id=mentor.tenant_id, student_user_id=student_id, mentor_user_id=mentor.id, status="pending_mentor", mentor_note=note)
        db.add(existing)
    else:
        existing.status, existing.mentor_note = "pending_mentor", note
    return existing


def mentor_confirm(db: Session, mentor: User, selection_id: UUID, note: str | None) -> MentorSelection:
    settings = _ensure_open(db, mentor.tenant_id)
    mentor_setting = mentor_settings(db, mentor.id, settings.default_capacity, lock=True)
    item = db.scalar(select(MentorSelection).where(MentorSelection.id == selection_id, MentorSelection.mentor_user_id == mentor.id).with_for_update())
    if item is None:
        _error("selection_not_found", status.HTTP_404_NOT_FOUND)
    if item.status != "pending_student":
        _error("selection_not_pending")
    _reserve_available(db, mentor.id, mentor_setting, settings.default_capacity)
    item.mentor_note = note
    return _confirm(db, item)


def mentor_reject(db: Session, mentor: User, selection_id: UUID, note: str | None) -> MentorSelection:
    _ensure_open(db, mentor.tenant_id)
    item = db.scalar(select(MentorSelection).where(MentorSelection.id == selection_id, MentorSelection.mentor_user_id == mentor.id).with_for_update())
    if item is None:
        _error("selection_not_found", status.HTTP_404_NOT_FOUND)
    if item.status not in ("pending_student", "pending_mentor"):
        _error("selection_not_pending")
    item.status, item.mentor_note = "rejected", note
    return item
