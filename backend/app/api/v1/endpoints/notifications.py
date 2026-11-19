from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select, update

from app.api.deps import CurrentUser, DbSession, require_super_admin
from app.models.subscription import InstitutionAdminScope
from app.models.user import User
from app.models.workspace import WorkspaceEvent
from app.services.admin_scope import is_administrator, is_super_admin
from app.services.workspace_events import record, school_admins

router = APIRouter(prefix="/notifications", tags=["Workspace notifications"])
admin_router = APIRouter(prefix="/admin/notifications", tags=["Institution reminders"])


def inbox_filter(user):
    roles = {role.code for role in user.roles} & {"student", "mentor"}
    if is_administrator(user):
        roles.add("admin")
    conditions = (
        WorkspaceEvent.tenant_id == user.tenant_id,
        WorkspaceEvent.recipient_id == user.id,
        WorkspaceEvent.workspace.in_(roles),
    )
    if "admin" in roles and not is_super_admin(user):
        schools = select(InstitutionAdminScope.institution_abbr).where(
            InstitutionAdminScope.tenant_id == user.tenant_id, InstitutionAdminScope.user_id == user.id)
        conditions += (or_(WorkspaceEvent.workspace != "admin", WorkspaceEvent.institution_abbr.in_(schools)),)
    return conditions


@router.get("")
def inbox(db: DbSession, user: CurrentUser, unread_only: bool = False,
          limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0)):
    conditions = inbox_filter(user)
    unread = db.scalar(select(func.count()).select_from(WorkspaceEvent).where(
        *conditions, WorkspaceEvent.read_at.is_(None)
    ))
    if unread_only:
        conditions += (WorkspaceEvent.read_at.is_(None),)
    total = db.scalar(select(func.count()).select_from(WorkspaceEvent).where(*conditions))
    rows = db.scalars(select(WorkspaceEvent).where(*conditions)
                     .order_by(WorkspaceEvent.created_at.desc(), WorkspaceEvent.id.desc())
                     .limit(limit).offset(offset)).all()
    actor_ids = {row.actor_id for row in rows if row.actor_id}
    actor_ids.update(UUID(row.details["counterpart_id"]) for row in rows if row.details.get("counterpart_id"))
    actors = dict(db.execute(select(User.id, User.full_name).where(
        User.tenant_id == user.tenant_id, User.id.in_(actor_ids)
    )).all()) if actor_ids else {}
    return {"unread": unread, "total": total, "items": [{
        "id": row.id, "kind": row.kind, "workspace": row.workspace, "subject_id": row.subject_id,
        "institution": row.institution_abbr, "details": row.details, "actor": actors.get(row.actor_id),
        "read_at": row.read_at, "created_at": row.created_at,
        "counterpart": actors.get(UUID(row.details["counterpart_id"])) if row.details.get("counterpart_id") else None,
    } for row in rows]}


@router.post("/read-all", status_code=204)
def read_all(db: DbSession, user: CurrentUser):
    db.execute(update(WorkspaceEvent).where(*inbox_filter(user), WorkspaceEvent.read_at.is_(None))
               .values(read_at=datetime.now(timezone.utc)))
    db.commit()


@router.post("/{event_id}/read", status_code=204)
def read_one(event_id: UUID, db: DbSession, user: CurrentUser):
    row = db.scalar(select(WorkspaceEvent).where(*inbox_filter(user), WorkspaceEvent.id == event_id))
    if row is None:
        raise HTTPException(404, detail={"code": "notification_not_found"})
    if row.read_at is None:
        row.read_at = datetime.now(timezone.utc)
        db.commit()


class ReminderRequest(BaseModel):
    institution: str = Field(min_length=1, max_length=12)
    recipient_id: UUID
    category: Literal["quota", "allocation", "issuance", "delivery"]


@admin_router.get("/recipients")
def recipients(db: DbSession, institution: str = Query(min_length=1, max_length=12),
               admin: User = Depends(require_super_admin)):
    institution = institution.strip().upper()
    return [{"id": user.id, "name": user.full_name, "username": user.username}
            for user in school_admins(db, admin.tenant_id, institution)]


@admin_router.post("/reminders", status_code=201)
def remind(payload: ReminderRequest, db: DbSession, admin: User = Depends(require_super_admin)):
    institution = payload.institution.strip().upper()
    if not any(user.id == payload.recipient_id for user in school_admins(db, admin.tenant_id, institution)):
        raise HTTPException(404, detail={"code": "institution_admin_not_found"})
    kind = f"reminder_{payload.category}"
    # Lock the sender so repeated clicks cannot create duplicate reminders across workers.
    db.scalar(select(User.id).where(User.id == admin.id).with_for_update())
    previous = db.scalar(select(WorkspaceEvent.id).where(
        WorkspaceEvent.tenant_id == admin.tenant_id, WorkspaceEvent.actor_id == admin.id,
        WorkspaceEvent.recipient_id == payload.recipient_id, WorkspaceEvent.institution_abbr == institution,
        WorkspaceEvent.kind == kind, WorkspaceEvent.read_at.is_(None),
    ).limit(1))
    if previous:
        return {"id": previous}
    event = record(db, admin.tenant_id, kind, actor_id=admin.id, recipient_id=payload.recipient_id,
                   workspace="admin", institution=institution)
    db.flush()
    event_id = event.id
    db.commit()
    return {"id": event_id}
