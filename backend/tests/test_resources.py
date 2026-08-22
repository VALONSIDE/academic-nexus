import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models import resource, tenant, user  # noqa: F401
from app.models.resource import Resource
from app.models.tenant import Tenant
from app.models.user import StudentProfile, User
from app.services import resources as resource_service


def test_resource_quota_and_profile_recommendation() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        organization = Tenant(slug="resource-test", name="Resource Test")
        db.add(organization)
        db.flush()
        student = User(tenant_id=organization.id, username="TEST_S1", full_name="Student", password_hash="hash")
        mentor = User(tenant_id=organization.id, username="TEST_T1", full_name="Mentor", password_hash="hash")
        db.add_all([student, mentor])
        db.flush()
        db.add(
            StudentProfile(
                user_id=student.id,
                research_interests=["natural language processing"],
                skills=["Python"],
                academic_performance="GPA 3.8",
                academic_goals="build an NLP project",
                research_experience="coursework",
            )
        )
        db.add_all(
            [
                Resource(
                    tenant_id=organization.id,
                    owner_user_id=mentor.id,
                    resource_type="course",
                    title="Natural language processing with Python",
                    description="NLP project practice",
                    topics=["natural language processing"],
                    tags=["Python"],
                    external_url="https://example.test/nlp",
                ),
                Resource(
                    tenant_id=organization.id,
                    owner_user_id=mentor.id,
                    resource_type="book",
                    title="Marine biology",
                    description="ocean ecology",
                    topics=["marine biology"],
                    tags=[],
                    external_url="https://example.test/ocean",
                ),
            ]
        )
        db.commit()
        db.refresh(student)

        quota = resource_service.quota_snapshot(db, mentor.id)
        assert quota.quota_bytes == 200 * resource_service.MEGABYTE
        resource_service.reserve_file_bytes(db, mentor.id, 1024)
        assert quota.used_bytes == 1024
        with pytest.raises(resource_service.ResourceError, match="resource_quota_exceeded"):
            resource_service.reserve_file_bytes(db, mentor.id, quota.quota_bytes)

        ranked = resource_service.recommended_resources(db, student, limit=2)
        assert ranked[0][0].title == "Natural language processing with Python"
        assert ranked[0][1] > ranked[1][1]
