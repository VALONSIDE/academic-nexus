from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.api.v1.endpoints.auth import login, start_activation
from app.api.v1.endpoints.profiles import complete_student_registration
from app.core.security import hash_password
from app.db.base import Base
from app.models import pre_registration, tenant, user  # noqa: F401
from app.models.pre_registration import PreRegistration, PreRegistrationBatch
from app.models.tenant import Tenant
from app.models.user import Role, User
from app.schemas.auth import ActivationRequest, LoginRequest
from app.schemas.profiles import StudentAcademicProfilePayload


def test_account_cannot_log_in_until_academic_portrait_is_completed() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        institution = Tenant(slug="cuc-pilot", name="CUC Pilot")
        db.add(institution)
        db.flush()
        student_role = Role(tenant_id=institution.id, code="student", name_zh="学生", name_en="Student")
        admin = User(tenant_id=institution.id, username="CUC_ADMIN", full_name="Admin", password_hash="hash")
        db.add_all([student_role, admin])
        db.flush()
        batch = PreRegistrationBatch(
            tenant_id=institution.id,
            uploaded_by_user_id=admin.id,
            source_filename="students.xlsx",
            row_count=1,
        )
        db.add(batch)
        db.flush()
        pre_registration = PreRegistration(
            tenant_id=institution.id,
            batch_id=batch.id,
            username="CUC_S20240001",
            role_code="student",
            full_name="张同学",
            academic_id="20240001",
            institution_abbr="CUC",
            institution_name_zh="中国传媒大学",
            college_name_zh="新闻学院",
            access_key_hash=hash_password("1234-ABCD-5678-9012"),
            access_key_fingerprint="a" * 64,
        )
        db.add(pre_registration)
        db.commit()

        activation = start_activation(
            ActivationRequest(
                username="CUC_S20240001",
                full_name="张同学",
                academic_id="20240001",
                access_key="1234-ABCD-5678-9012",
                password="AcademicNexus2026",
                terms_accepted=True,
                privacy_accepted=True,
            ),
            db,
        )
        assert activation.role == "student"
        pending = db.scalar(select(User).where(User.username == "CUC_S20240001"))
        assert pending is not None and not pending.is_active

        completed = complete_student_registration(
            StudentAcademicProfilePayload(
                research_interests=["人工智能"],
                skills=["Python"],
                academic_performance="GPA 3.8/4.0",
                academic_goals="申请人工智能方向研究生。",
                research_experience="参与校级科研训练项目。",
            ),
            pending,
            db,
        )
        assert completed.user.is_active
        assert db.scalar(select(PreRegistration.status).where(PreRegistration.id == pre_registration.id)) == "activated"
        assert login(LoginRequest(username="CUC_S20240001", password="AcademicNexus2026"), db).user.username == "CUC_S20240001"
