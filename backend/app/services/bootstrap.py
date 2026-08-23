from sqlalchemy import select

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.session import SessionLocal
# Register all tables referenced by User foreign keys before a clean-database
# bootstrap.  This makes the initializer safe to run outside FastAPI startup.
from app.models import pre_registration  # noqa: F401
from app.models.tenant import Tenant
from app.models.user import Role, User

ROLE_SEEDS = (
    ("student", "学生", "Student"),
    ("mentor", "导师", "Mentor"),
    ("admin", "管理员", "Administrator"),
    ("super_admin", "超级管理员", "Super administrator"),
    ("institution_admin", "院校管理员", "Institution administrator"),
)


def ensure_bootstrap_data() -> None:
    """Create the pilot tenant, standard roles, and first admin exactly once / 首次初始化试点租户、角色及管理员。"""
    settings = get_settings()
    with SessionLocal() as db:
        tenant = db.scalar(select(Tenant).where(Tenant.slug == settings.default_tenant_slug))
        if tenant is None:
            tenant = Tenant(slug=settings.default_tenant_slug, name=settings.default_tenant_name)
            db.add(tenant)
            db.flush()

        roles: dict[str, Role] = {}
        for code, name_zh, name_en in ROLE_SEEDS:
            role = db.scalar(select(Role).where(Role.tenant_id == tenant.id, Role.code == code))
            if role is None:
                role = Role(tenant_id=tenant.id, code=code, name_zh=name_zh, name_en=name_en)
                db.add(role)
            roles[code] = role
        db.flush()

        admin = db.scalar(select(User).where(User.tenant_id == tenant.id, User.email == settings.initial_admin_email.lower()))
        if admin is None:
            admin = User(
                tenant_id=tenant.id,
                username=settings.initial_admin_username.upper(),
                email=settings.initial_admin_email.lower(),
                full_name="AcademicNexus Administrator",
                password_hash=hash_password(settings.initial_admin_password),
                preferred_locale="zh-CN",
                is_active=True,
                is_verified=True,
            )
            admin.roles.append(roles["admin"])
            admin.roles.append(roles["super_admin"])
            db.add(admin)
        elif admin.username is None:
            # Migration path for an administrator created by the previous login system.
            admin.username = settings.initial_admin_username.upper()
        if not any(role.code == "super_admin" for role in admin.roles):
            admin.roles.append(roles["super_admin"])
        db.commit()
