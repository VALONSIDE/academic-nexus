"""REST API for the core student--mentor mutual-selection flow."""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import DbSession, require_roles, require_super_admin
from app.models.selection import MentorSelection, MentorSelectionSetting, StudentSelectionSetting
from app.models.user import User
from app.schemas.selection import (
    AdminSelectionBulkReleaseRequest, AdminSelectionRecordListResponse, AdminSelectionRecordResponse, AdminSelectionUserResponse, AdminSelectionUserUpdate, MentorSelectionSettingsResponse, MentorSelectionSettingsUpdate, NotePayload,
    SelectionCandidate, SelectionCandidateListResponse, SelectionResponse,
    SelectionSettingsResponse, SelectionSettingsUpdate,
)
from app.services.matching import score_student_to_mentor
from app.services.selection import (
    capacity_counts, capacity_of, mentor_confirm, mentor_invite, mentor_reject,
    mentor_settings, student_cancel, student_choose, student_settings, tenant_settings,
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
    return MentorSelectionSettingsResponse(capacity=capacity, is_exempt=item.is_exempt, selection_mode=item.selection_mode, confirmed_count=confirmed, invitation_count=invitations, available_slots=max(0, capacity - confirmed - invitations))


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
    if payload.capacity is not None:
        confirmed, invitations = capacity_counts(db, mentor.id)
        if payload.capacity < confirmed + invitations:
            from fastapi import HTTPException
            raise HTTPException(status_code=409, detail={"code": "capacity_below_active_selections"})
        item.capacity = payload.capacity
    if payload.selection_mode is not None:
        item.selection_mode = payload.selection_mode
    db.commit()
    return _mentor_settings_response(db, mentor)


@router.get("/mentor/candidates", response_model=SelectionCandidateListResponse)
def mentor_candidates(db: DbSession, mentor: User = Depends(require_roles("mentor"))) -> SelectionCandidateListResponse:
    rows = list(db.scalars(select(MentorSelection).where(MentorSelection.mentor_user_id == mentor.id).order_by(MentorSelection.updated_at.desc())).all())
    student_ids = [item.student_user_id for item in rows]
    students = {
        item.id: item
        for item in db.scalars(select(User).options(selectinload(User.student_profile)).where(User.id.in_(student_ids))).all()
    } if student_ids else {}
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
def get_admin_settings(db: DbSession, admin: User = Depends(require_super_admin)) -> SelectionSettingsResponse:
    item = tenant_settings(db, admin.tenant_id)
    return SelectionSettingsResponse(is_open=item.is_open, default_capacity=item.default_capacity, default_student_choice_limit=item.default_student_choice_limit)


@admin_router.patch("/settings", response_model=SelectionSettingsResponse)
def update_admin_settings(payload: SelectionSettingsUpdate, db: DbSession, admin: User = Depends(require_super_admin)) -> SelectionSettingsResponse:
    item = tenant_settings(db, admin.tenant_id, lock=True)
    if payload.is_open is not None:
        item.is_open = payload.is_open
    if payload.default_capacity is not None:
        item.default_capacity = payload.default_capacity
    if payload.default_student_choice_limit is not None:
        item.default_student_choice_limit = payload.default_student_choice_limit
    db.commit()
    return SelectionSettingsResponse(is_open=item.is_open, default_capacity=item.default_capacity, default_student_choice_limit=item.default_student_choice_limit)


@admin_router.get("/users", response_model=list[AdminSelectionUserResponse])
def list_selection_users(
    db: DbSession,
    admin: User = Depends(require_super_admin),
    role: str = "student",
) -> list[AdminSelectionUserResponse]:
    if role not in {"student", "mentor"}:
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail={"code": "invalid_role"})
    global_settings = tenant_settings(db, admin.tenant_id)
    users = db.scalars(select(User).options(selectinload(User.roles), selectinload(User.student_profile), selectinload(User.mentor_profile)).where(User.tenant_id == admin.tenant_id, User.roles.any(code=role)).order_by(User.full_name)).all()
    result: list[AdminSelectionUserResponse] = []
    for user in users:
        profile = user.student_profile if role == "student" else user.mentor_profile
        if role == "student":
            item = student_settings(db, user.id)
            result.append(AdminSelectionUserResponse(user_id=user.id, username=user.username or "", full_name=user.full_name, role="student", institution_name_zh=profile.university if profile else None, college_name_zh=profile.department if profile else None, choice_limit=item.choice_limit, is_exempt=item.is_exempt))
        else:
            item = mentor_settings(db, user.id, global_settings.default_capacity)
            result.append(AdminSelectionUserResponse(user_id=user.id, username=user.username or "", full_name=user.full_name, role="mentor", institution_name_zh=profile.university if profile else None, college_name_zh=profile.department if profile else None, capacity=item.capacity, is_exempt=item.is_exempt, selection_mode=item.selection_mode))
    db.commit()
    return result


@admin_router.patch("/users/{user_id}", response_model=AdminSelectionUserResponse)
def update_selection_user(
    user_id: UUID,
    payload: AdminSelectionUserUpdate,
    db: DbSession,
    admin: User = Depends(require_super_admin),
) -> AdminSelectionUserResponse:
    user = db.scalar(select(User).options(selectinload(User.roles), selectinload(User.student_profile), selectinload(User.mentor_profile)).where(User.id == user_id, User.tenant_id == admin.tenant_id).with_for_update())
    if user is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail={"code": "user_not_found"})
    if any(role.code == "student" for role in user.roles):
        item = student_settings(db, user.id, lock=True)
        if payload.use_default:
            item.choice_limit = None
            item.is_exempt = False
        elif payload.choice_limit is not None:
            item.choice_limit = payload.choice_limit
        if payload.is_exempt is not None: item.is_exempt = payload.is_exempt
        db.commit()
        profile = user.student_profile
        return AdminSelectionUserResponse(user_id=user.id, username=user.username or "", full_name=user.full_name, role="student", institution_name_zh=profile.university if profile else None, college_name_zh=profile.department if profile else None, choice_limit=item.choice_limit, is_exempt=item.is_exempt)
    if any(role.code == "mentor" for role in user.roles):
        item = mentor_settings(db, user.id, tenant_settings(db, admin.tenant_id).default_capacity, lock=True)
        if payload.use_default:
            item.capacity = None
            item.is_exempt = False
        elif payload.capacity is not None:
            item.capacity = payload.capacity
        if payload.is_exempt is not None: item.is_exempt = payload.is_exempt
        if payload.selection_mode is not None: item.selection_mode = payload.selection_mode
        db.commit()
        profile = user.mentor_profile
        return AdminSelectionUserResponse(user_id=user.id, username=user.username or "", full_name=user.full_name, role="mentor", institution_name_zh=profile.university if profile else None, college_name_zh=profile.department if profile else None, capacity=item.capacity, is_exempt=item.is_exempt, selection_mode=item.selection_mode)
    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail={"code": "user_not_found"})


@admin_router.get("/records", response_model=AdminSelectionRecordListResponse)
def list_selection_records(
    db: DbSession,
    admin: User = Depends(require_super_admin),
    selection_status: str | None = None,
    search: str = "",
) -> AdminSelectionRecordListResponse:
    statement = select(MentorSelection).where(MentorSelection.tenant_id == admin.tenant_id)
    if selection_status is not None:
        if selection_status not in {"pending_student", "pending_mentor", "confirmed", "rejected", "cancelled"}:
            from fastapi import HTTPException
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
    ids = list(set(selection_ids))
    records = db.scalars(
        select(MentorSelection)
        .where(MentorSelection.id.in_(ids), MentorSelection.tenant_id == admin.tenant_id)
        .with_for_update()
    ).all()
    if len(records) != len(ids):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail={"code": "selection_not_found"})
    for item in records:
        item.status = "cancelled"
        item.confirmed_at = None
    db.commit()


@admin_router.post("/records/{selection_id}/release", status_code=204)
def release_selection_record(
    selection_id: UUID,
    db: DbSession,
    admin: User = Depends(require_super_admin),
) -> None:
    """Administrator override equivalent to releasing a locked historical selection."""
    _release_selection_records(db, admin, [selection_id])


@admin_router.post("/records/bulk-release", status_code=204)
def bulk_release_selection_records(
    payload: AdminSelectionBulkReleaseRequest,
    db: DbSession,
    admin: User = Depends(require_super_admin),
) -> None:
    _release_selection_records(db, admin, payload.selection_ids)
