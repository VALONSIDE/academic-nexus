from sqlalchemy import select

from app.models.subscription import InstitutionAdminScope
from app.models.user import User
from app.models.workspace import WorkspaceEvent


def record(db, tenant_id, kind, *, actor_id=None, recipient_id=None, workspace=None,
           institution=None, subject_id=None, **details):
    event = WorkspaceEvent(
        tenant_id=tenant_id, kind=kind, actor_id=actor_id, recipient_id=recipient_id,
        workspace=workspace, institution_abbr=institution, subject_id=subject_id, details=details,
    )
    db.add(event)
    return event


def school_admins(db, tenant_id, institution):
    return db.scalars(
        select(User).join(InstitutionAdminScope, InstitutionAdminScope.user_id == User.id)
        .where(User.tenant_id == tenant_id, User.is_active.is_(True),
               User.roles.any(code="institution_admin"), InstitutionAdminScope.tenant_id == tenant_id,
               InstitutionAdminScope.institution_abbr == institution)
        .order_by(User.full_name, User.id)
    ).unique().all()


def notify_school_admins(db, tenant_id, institution, kind, *, actor_id=None, **details):
    for admin in school_admins(db, tenant_id, institution):
        if admin.id != actor_id:
            record(db, tenant_id, kind, actor_id=actor_id, recipient_id=admin.id,
                   workspace="admin", institution=institution, **details)


def selection_event(db, item, kind, *, actor_id=None, recipient_role=None):
    for role, recipient in (("student", item.student_user_id), ("mentor", item.mentor_user_id)):
        if recipient_role is not None and role != recipient_role:
            continue
        counterpart = item.mentor_user_id if role == "student" else item.student_user_id
        record(db, item.tenant_id, kind, actor_id=actor_id, recipient_id=recipient,
               workspace=role, subject_id=item.id, counterpart_id=str(counterpart))
