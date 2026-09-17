"""Server-side role and institution-scope checks for administration."""

from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.subscription import InstitutionAdminScope
from app.models.user import User

LEGACY_SUPER_ADMIN_ROLE = "admin"
SUPER_ADMIN_ROLES = frozenset({LEGACY_SUPER_ADMIN_ROLE, "super_admin"})
INSTITUTION_ADMIN_ROLE = "institution_admin"
ADMINISTRATOR_ROLES = SUPER_ADMIN_ROLES | {INSTITUTION_ADMIN_ROLE}


def role_codes(user: User) -> set[str]:
    return {role.code for role in user.roles}


def is_super_admin(user: User) -> bool:
    """Existing ``admin`` accounts remain super administrators during migration."""
    return bool(role_codes(user).intersection(SUPER_ADMIN_ROLES))


def is_institution_admin(user: User) -> bool:
    return INSTITUTION_ADMIN_ROLE in role_codes(user)


def is_administrator(user: User) -> bool:
    return bool(role_codes(user).intersection(ADMINISTRATOR_ROLES))


def institution_admin_abbrs(db: Session, user: User) -> set[str]:
    if is_super_admin(user):
        return set()
    return set(
        db.scalars(
            select(InstitutionAdminScope.institution_abbr).where(
                InstitutionAdminScope.tenant_id == user.tenant_id,
                InstitutionAdminScope.user_id == user.id,
            )
        ).all()
    )


def user_institution_abbr(user: User) -> str | None:
    if user.student_profile is not None:
        return user.student_profile.institution_abbr
    if user.mentor_profile is not None:
        return user.mentor_profile.institution_abbr
    return None


def can_manage_institution(db: Session, admin: User, institution_abbr: str | None) -> bool:
    return is_super_admin(admin) or (institution_abbr is not None and institution_abbr in institution_admin_abbrs(db, admin))


def can_manage_user(db: Session, admin: User, user: User) -> bool:
    return admin.tenant_id == user.tenant_id and can_manage_institution(db, admin, user_institution_abbr(user))


def has_any_institution_scope(db: Session, admin: User, institutions: Iterable[str]) -> bool:
    scopes = institution_admin_abbrs(db, admin)
    return bool(scopes.intersection(institutions))
