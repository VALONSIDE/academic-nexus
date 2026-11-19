"""REST API for the core student--mentor mutual-selection flow."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.api.deps import DbSession, require_roles, require_super_admin, require_administrator
from app.models.selection import MentorSelection, MentorSelectionSetting, StudentSelectionSetting
from app.models.user import User, StudentProfile, MentorProfile
from app.services.admin_scope import can_manage_user, institution_admin_abbrs, is_super_admin, user_institution_abbr
from app.services.workspace_events import record, selection_event
from app.schemas.selection import (
    AdminSelectionBulkReleaseRequest, AdminSelectionRecordListResponse, AdminSelectionRecordResponse, AdminSelectionUserResponse, AdminSelectionUserUpdate, MentorSelectionSettingsResponse, MentorSelectionSettingsUpdate, NotePayload,
    SelectionCandidate, SelectionCandidateListResponse, SelectionResponse,
    SelectionSettingsResponse, SelectionSettingsUpdate,
)
from app.services.matching import score_student_to_mentor
from app.services.selection import (
    capacity_counts, capacity_of, mentor_confirm, mentor_invite, mentor_reject,
    student_choice_count, mentor_settings, student_cancel, student_choose, student_settings, tenant_settings,
)

router = APIRouter(prefix="/selection", tags=["Mutual selection / 双向选择"])
admin_router = APIRouter(prefix="/admin/selection", tags=["Selection administration / 双向选择管理"])


def _selection(item: MentorSelection) -> SelectionResponse:
    return SelectionResponse.model_validate(item, from_attributes=True)


def _mentor_settings_response(db: DbSession, mentor: User) -> MentorSelectionSettingsResponse:
    global_settings = tenant_settings(db, mentor.tenant_id)
    item = mentor_settings(db, mentor.id, global_settings.default_capacity)
    confirmed, invitations = capacity_counts(db, mentor.id)
    capacity = capacity_of(item, global_settings.default_capacity)
    return MentorSelectionSettingsResponse(capacity=capacity, is_exempt=item.is_exempt, selection_mode=item.selection_mode, confirmed_count=confirmed, invitation_count=invitations, available_slots=None if item.is_exempt else max(0, capacity - confirmed - invitations))


def _selection_record_response(item: MentorSelection, users: dict[UUID, User]) -> AdminSelectionRecordResponse:
    student = users[item.student_user_id]
    mentor = users[item.mentor_user_id]
    return AdminSelectionRecordResponse(
        id=item.id,
        status=item.status,
        student_user_id=student.id,
        student_name=student.full_name,
        student_username=student.username or "",
        student_institution_name_zh=student.student_profile.university if student.student_profile else None,
        student_college_name_zh=student.student_profile.department if student.student_profile else None,
        mentor_user_id=mentor.id,
        mentor_name=mentor.full_name,
        mentor_username=mentor.username or "",
        mentor_institution_name_zh=mentor.mentor_profile.university if mentor.mentor_profile else None,
        mentor_college_name_zh=mentor.mentor_profile.department if mentor.mentor_profile else None,
        created_at=item.created_at,
        updated_at=item.updated_at,
        confirmed_at=item.confirmed_at,
    )


@router.get("/student/me", response_model=list[SelectionResponse])
def student_selections(db: DbSession, student: User = Depends(require_roles("student"))) -> list[SelectionResponse]:
    return [_selection(item) for item in db.scalars(select(MentorSelection).where(MentorSelection.student_user_id == student.id).order_by(MentorSelection.updated_at.desc())).all()]


@router.post("/student/mentors/{mentor_id}", response_model=SelectionResponse)
def choose_mentor(mentor_id: UUID, payload: NotePayload, db: DbSession, student: User = Depends(require_roles("student"))) -> SelectionResponse:
    item = student_choose(db, student, mentor_id, payload.note)
    db.commit()
    db.refresh(item)
    return _selection(item)


@router.post("/student/cancel", status_code=204)
def cancel_choice(db: DbSession, student: User = Depends(require_roles("student"))) -> None:
    student_cancel(db, student)
    db.commit()


@router.post("/student/selections/{selection_id}/cancel", status_code=204)
def cancel_specific_choice(selection_id: UUID, db: DbSession, student: User = Depends(require_roles("student"))) -> None:
    """Cancel the exact card selected by the student, including exception users with several choices."""
    student_cancel(db, student, selection_id)
    db.commit()


@router.get("/mentor/settings", response_model=MentorSelectionSettingsResponse)
def get_mentor_settings(db: DbSession, mentor: User = Depends(require_roles("mentor"))) -> MentorSelectionSettingsResponse:
    return _mentor_settings_response(db, mentor)


@router.patch("/mentor/settings", response_model=MentorSelectionSettingsResponse)
def update_mentor_settings(payload: MentorSelectionSettingsUpdate, db: DbSession, mentor: User = Depends(require_roles("mentor"))) -> MentorSelectionSettingsResponse:
    global_settings = tenant_settings(db, mentor.tenant_id, lock=True)
    item = mentor_settings(db, mentor.id, global_settings.default_capacity, lock=True)
    if (
        payload.capacity not in (None, capacity_of(item, global_settings.default_capacity))
        or payload.selection_mode not in (None, item.selection_mode)
    ):
        raise HTTPException(status_code=403, detail={"code": "selection_settings_administrator_only"})
    db.commit()
    return _mentor_settings_response(db, mentor)


@router.get("/mentor/candidates", response_model=SelectionCandidateListResponse)
def mentor_candidates(db: DbSession, mentor: User = Depends(require_roles("mentor"))) -> SelectionCandidateListResponse:
    rows = list(db.scalars(select(MentorSelection).where(MentorSelection.mentor_user_id == mentor.id).order_by(MentorSelection.updated_at.desc())).all())
    student_ids = [item.student_user_id for item in rows]
    school = user_institution_abbr(mentor)
    students = {}
    if student_ids and school:
        query = select(User).options(selectinload(User.student_profile)).where(
            User.id.in_(student_ids), User.tenant_id == mentor.tenant_id,
            User.is_active.is_(True), User.roles.any(code="student"),
            User.student_profile.has(StudentProfile.institution_abbr == school),
        )
        students = {student.id: student for student in db.scalars(query)}
    candidates: list[SelectionCandidate] = []
    for item in rows:
        student = students.get(item.student_user_id)
        if student is None or student.student_profile is None or mentor.mentor_profile is None:
            continue
        score = score_student_to_mentor(student.student_profile, mentor.mentor_profile).score
        profile = student.student_profile
        candidates.append(SelectionCandidate(selection=_selection(item), full_name=student.full_name, username=student.username or "", university=profile.university, department=profile.department, major=profile.major, research_interests=profile.research_interests or [], skills=profile.skills or [], match_score=score))
    return SelectionCandidateListResponse(settings=_mentor_settings_response(db, mentor), items=candidates)


@router.post("/mentor/students/{student_id}/invite", response_model=SelectionResponse)
def invite_student(student_id: UUID, payload: NotePayload, db: DbSession, mentor: User = Depends(require_roles("mentor"))) -> SelectionResponse:
    item = mentor_invite(db, mentor, student_id, payload.note)
    db.commit()
    db.refresh(item)
    return _selection(item)


@router.post("/mentor/selections/{selection_id}/confirm", response_model=SelectionResponse)
def confirm_student(selection_id: UUID, payload: NotePayload, db: DbSession, mentor: User = Depends(require_roles("mentor"))) -> SelectionResponse:
    item = mentor_confirm(db, mentor, selection_id, payload.note)
    db.commit()
    db.refresh(item)
    return _selection(item)


@router.post("/mentor/selections/{selection_id}/reject", response_model=SelectionResponse)
def reject_student(selection_id: UUID, payload: NotePayload, db: DbSession, mentor: User = Depends(require_roles("mentor"))) -> SelectionResponse:
    item = mentor_reject(db, mentor, selection_id, payload.note)
    db.commit()
    db.refresh(item)
    return _selection(item)


@admin_router.get("/settings", response_model=SelectionSettingsResponse)
def get_admin_settings(db: DbSession, admin: User = Depends(require_administrator)) -> SelectionSettingsResponse:
    item = tenant_settings(db, admin.tenant_id)
    return SelectionSettingsResponse(is_open=item.is_open, default_capacity=item.default_capacity, default_student_choice_limit=item.default_student_choice_limit)


@admin_router.patch("/settings", response_model=SelectionSettingsResponse)
def update_admin_settings(payload: SelectionSettingsUpdate, db: DbSession, admin: User = Depends(require_super_admin)) -> SelectionSettingsResponse:
    item = tenant_settings(db, admin.tenant_id, lock=True)
    old_open = item.is_open
    active_tenant = MentorSelection.tenant_id == admin.tenant_id
    if payload.default_capacity is not None and payload.default_capacity < item.default_capacity:
        used = select(MentorSelection.mentor_user_id).outerjoin(
            MentorSelectionSetting, MentorSelectionSetting.mentor_user_id == MentorSelection.mentor_user_id
        ).where(active_tenant, MentorSelection.status.in_(("confirmed", "pending_mentor")),
                MentorSelectionSetting.capacity.is_(None),
                MentorSelectionSetting.is_exempt.is_not(True)
        ).group_by(MentorSelection.mentor_user_id).having(func.count() > payload.default_capacity)
        if db.scalar(used.limit(1)):
            raise HTTPException(409, detail={"code": "selection_quota_below_usage"})
    if payload.default_student_choice_limit is not None and payload.default_student_choice_limit < item.default_student_choice_limit:
        used = select(MentorSelection.student_user_id).outerjoin(
            StudentSelectionSetting, StudentSelectionSetting.student_user_id == MentorSelection.student_user_id
        ).where(active_tenant, MentorSelection.status == "pending_student",
                StudentSelectionSetting.choice_limit.is_(None),
                StudentSelectionSetting.is_exempt.is_not(True)
        ).group_by(MentorSelection.student_user_id).having(func.count() > payload.default_student_choice_limit)
        if db.scalar(used.limit(1)):
            raise HTTPException(409, detail={"code": "selection_quota_below_usage"})
    if payload.is_open is not None:
        item.is_open = payload.is_open
    if payload.default_capacity is not None:
        item.default_capacity = payload.default_capacity
    if payload.default_student_choice_limit is not None:
        item.default_student_choice_limit = payload.default_student_choice_limit
    if item.is_open != old_open:
        for role in ("student", "mentor"):
            recipients = db.scalars(select(User.id).where(
                User.tenant_id == admin.tenant_id, User.is_active.is_(True), User.roles.any(code=role)))
            for recipient in recipients:
                record(db, admin.tenant_id, "selection_window_opened" if item.is_open else "selection_window_closed",
                       actor_id=admin.id, recipient_id=recipient, workspace=role)
    db.commit()
    return SelectionSettingsResponse(is_open=item.is_open, default_capacity=item.default_capacity, default_student_choice_limit=item.default_student_choice_limit)


def selection_user_snapshot(db, user, role, defaults):
    profile = user.student_profile if role == "student" else user.mentor_profile
    item = student_settings(db, user.id) if role == "student" else mentor_settings(db, user.id, defaults.default_capacity)
    if role == "student":
        pending = student_choice_count(db, user.id)
        confirmed = db.scalar(select(func.count()).select_from(MentorSelection).where(
            MentorSelection.student_user_id == user.id, MentorSelection.status == "confirmed"
        )) or 0
    else:
        confirmed, pending = capacity_counts(db, user.id)
    override = item.choice_limit if role == "student" else item.capacity
    default_limit = defaults.default_student_choice_limit if role == "student" else defaults.default_capacity
    effective_limit = override if override is not None else default_limit
    occupied = pending + confirmed if role == "mentor" else pending
    available = None if item.is_exempt else max(0, effective_limit - occupied)
    if role == "student" and confirmed:
        available = 0
    return AdminSelectionUserResponse(
        user_id=user.id, username=user.username or "", full_name=user.full_name, role=role,
        institution_name_zh=profile.university if profile else None,
        college_name_zh=profile.department if profile else None,
        choice_limit=override if role == "student" else None, capacity=override if role == "mentor" else None,
        is_exempt=item.is_exempt, selection_mode=getattr(item, "selection_mode", None),
        default_limit=default_limit, effective_limit=effective_limit, pending_count=pending,
        confirmed_count=confirmed, available=available,
    )


@router.get("/student/settings", response_model=AdminSelectionUserResponse)
def get_student_settings(db: DbSession, student: User = Depends(require_roles("student"))):
    return selection_user_snapshot(db, student, "student", tenant_settings(db, student.tenant_id))


@admin_router.get("/users", response_model=list[AdminSelectionUserResponse])
def list_selection_users(db: DbSession, admin: User = Depends(require_administrator), role: str = "student"):
    if role not in {"student", "mentor"}:
        raise HTTPException(422, detail={"code": "invalid_role"})
    defaults = tenant_settings(db, admin.tenant_id)
    statement = select(User).options(selectinload(User.student_profile), selectinload(User.mentor_profile)).where(
        User.tenant_id == admin.tenant_id, User.roles.any(code=role))
    if not is_super_admin(admin):
        scopes = institution_admin_abbrs(db, admin)
        condition = (User.student_profile.has(StudentProfile.institution_abbr.in_(scopes)) if role == "student"
                     else User.mentor_profile.has(MentorProfile.institution_abbr.in_(scopes)))
        statement = statement.where(condition)
    result = [selection_user_snapshot(db, user, role, defaults)
              for user in db.scalars(statement.order_by(User.full_name, User.id))]
    db.commit()
    return result


@admin_router.patch("/users/{user_id}", response_model=AdminSelectionUserResponse)
def update_selection_user(user_id: UUID, payload: AdminSelectionUserUpdate, db: DbSession,
                          admin: User = Depends(require_administrator)):
    defaults = tenant_settings(db, admin.tenant_id, lock=True)
    user = db.scalar(select(User).where(User.id == user_id, User.tenant_id == admin.tenant_id).with_for_update())
    if user is None or not can_manage_user(db, admin, user):
        raise HTTPException(404, detail={"code": "user_not_found"})
    roles = {role.code for role in user.roles}
    if "student" in roles:
        role, field, override = "student", "choice_limit", payload.choice_limit
        item = student_settings(db, user.id, lock=True)
        default = defaults.default_student_choice_limit
        used = student_choice_count(db, user.id)
    elif "mentor" in roles:
        role, field, override = "mentor", "capacity", payload.capacity
        item = mentor_settings(db, user.id, defaults.default_capacity, lock=True)
        default = defaults.default_capacity
        used = sum(capacity_counts(db, user.id))
    else:
        raise HTTPException(404, detail={"code": "user_not_found"})
    old = (getattr(item, field), item.is_exempt, getattr(item, "selection_mode", None))
    if payload.use_default:
        setattr(item, field, None)
        item.is_exempt = False
        if role == "mentor":
            item.selection_mode = "manual"
    else:
        if field in payload.model_fields_set:
            setattr(item, field, override)
        if payload.is_exempt is not None:
            item.is_exempt = payload.is_exempt
        if role == "mentor" and payload.selection_mode:
            item.selection_mode = payload.selection_mode
    limit = getattr(item, field) or default
    if not item.is_exempt and limit < used:
        raise HTTPException(409, detail={"code": "selection_quota_below_usage"})
    if old != (getattr(item, field), item.is_exempt, getattr(item, "selection_mode", None)):
        record(db, admin.tenant_id, "selection_quota_changed", actor_id=admin.id, recipient_id=user.id,
               workspace=role, limit=limit, exempt=item.is_exempt)
    result = selection_user_snapshot(db, user, role, defaults)
    db.commit()
    return result


@admin_router.get("/records", response_model=AdminSelectionRecordListResponse)
def list_selection_records(
    db: DbSession,
    admin: User = Depends(require_administrator),
    selection_status: str | None = None,
    search: str = "",
) -> AdminSelectionRecordListResponse:
    statement = select(MentorSelection).where(MentorSelection.tenant_id == admin.tenant_id)
    if not is_super_admin(admin):
        scopes = institution_admin_abbrs(db, admin)
        statement = statement.where(
            MentorSelection.student_user_id.in_(select(StudentProfile.user_id).where(StudentProfile.institution_abbr.in_(scopes))),
            MentorSelection.mentor_user_id.in_(select(MentorProfile.user_id).where(MentorProfile.institution_abbr.in_(scopes))))
    if selection_status is not None:
        if selection_status not in {"pending_student", "pending_mentor", "confirmed", "rejected", "cancelled"}:
            raise HTTPException(status_code=422, detail={"code": "invalid_selection_status"})
        statement = statement.where(MentorSelection.status == selection_status)
    records = list(db.scalars(statement.order_by(MentorSelection.updated_at.desc())).all())
    user_ids = {item.student_user_id for item in records} | {item.mentor_user_id for item in records}
    users = {
        user.id: user
        for user in db.scalars(
            select(User)
            .options(selectinload(User.student_profile), selectinload(User.mentor_profile))
            .where(User.id.in_(user_ids))
        ).all()
    } if user_ids else {}
    normalized_search = search.strip().casefold()
    if normalized_search:
        records = [
            item for item in records
            if normalized_search in (users[item.student_user_id].full_name or "").casefold()
            or normalized_search in (users[item.student_user_id].username or "").casefold()
            or normalized_search in (users[item.mentor_user_id].full_name or "").casefold()
            or normalized_search in (users[item.mentor_user_id].username or "").casefold()
        ]
    return AdminSelectionRecordListResponse(items=[_selection_record_response(item, users) for item in records], total=len(records))


def _release_selection_records(db: DbSession, admin: User, selection_ids: list[UUID]) -> None:
    tenant_settings(db, admin.tenant_id, lock=True)
    ids = sorted(set(selection_ids))
    records = db.scalars(
        select(MentorSelection)
        .where(MentorSelection.id.in_(ids), MentorSelection.tenant_id == admin.tenant_id)
        .with_for_update()
    ).all()
    if len(records) != len(ids):
        raise HTTPException(status_code=404, detail={"code": "selection_not_found"})
    for item in records:
        student, mentor = db.get(User, item.student_user_id), db.get(User, item.mentor_user_id)
        if not (student and mentor and can_manage_user(db, admin, student) and can_manage_user(db, admin, mentor)):
            raise HTTPException(404, detail={"code": "selection_not_found"})
        if item.status not in {"pending_student", "pending_mentor", "confirmed"}:
            continue
        selection_event(db, item, "selection_released", actor_id=admin.id)
        item.status = "cancelled"
        item.confirmed_at = None
    db.commit()


@admin_router.post("/records/{selection_id}/release", status_code=204)
def release_selection_record(
    selection_id: UUID,
    db: DbSession,
    admin: User = Depends(require_administrator),
) -> None:
    """Administrator override equivalent to releasing a locked historical selection."""
    _release_selection_records(db, admin, [selection_id])


@admin_router.post("/records/bulk-release", status_code=204)
def bulk_release_selection_records(
    payload: AdminSelectionBulkReleaseRequest,
    db: DbSession,
    admin: User = Depends(require_administrator),
) -> None:
    _release_selection_records(db, admin, payload.selection_ids)
