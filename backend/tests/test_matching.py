from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models import tenant, user  # noqa: F401
from app.models.tenant import Tenant
from app.models.user import MentorProfile, Role, StudentProfile, User
from app.services.matching import mentor_recommendations, score_student_to_mentor, student_candidates


def test_profile_hybrid_score_is_explainable_and_rewards_shared_research_tags() -> None:
    student = StudentProfile(
        research_interests=["natural language processing", "learning technology"],
        skills=["Python", "data analysis"],
        academic_goals="weekly feedback and a research paper",
        research_experience="education data project",
    )
    aligned_mentor = MentorProfile(
        research_directions=["natural language processing", "educational AI"],
        representative_papers=["NLP for education"],
        research_projects="education data project",
        mentoring_style="weekly feedback",
    )
    unrelated_mentor = MentorProfile(
        research_directions=["marine biology"],
        representative_papers=["Ocean ecology"],
        research_projects="field samples",
        mentoring_style="monthly seminar",
    )

    aligned = score_student_to_mentor(student, aligned_mentor)
    unrelated = score_student_to_mentor(student, unrelated_mentor)

    assert aligned.score > unrelated.score
    research_factor = next(item for item in aligned.factors if item.code == "research_alignment")
    assert research_factor.score > 0
    assert "natural language processing" in research_factor.shared_terms


def test_recommendations_are_ranked_for_both_student_and_mentor_views() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        organization = Tenant(slug="matching-test", name="Matching Test")
        db.add(organization)
        db.flush()
        student_role = Role(tenant_id=organization.id, code="student", name_zh="学生", name_en="Student")
        mentor_role = Role(tenant_id=organization.id, code="mentor", name_zh="导师", name_en="Mentor")
        student = User(tenant_id=organization.id, username="TEST_S1", full_name="Student", password_hash="hash")
        mentor = User(tenant_id=organization.id, username="TEST_T1", full_name="Mentor", password_hash="hash")
        student.roles.append(student_role)
        mentor.roles.append(mentor_role)
        db.add_all([student, mentor])
        db.flush()
        db.add_all(
            [
                StudentProfile(
                    user_id=student.id, institution_abbr="TEST", profile_completed_at=datetime.now(timezone.utc),
                    research_interests=["natural language processing"],
                    skills=["Python"],
                    academic_performance="GPA 3.8",
                    academic_goals="NLP research",
                    research_experience="NLP project",
                ),
                MentorProfile(
                    user_id=mentor.id, institution_abbr="TEST", profile_completed_at=datetime.now(timezone.utc),
                    research_directions=["natural language processing"],
                    representative_papers=["NLP"],
                    research_projects="NLP project",
                    mentoring_style="weekly feedback",
                ),
            ]
        )
        db.commit()
        db.refresh(student)
        db.refresh(mentor)

        mentor_results = mentor_recommendations(db, student, limit=10)
        student_results = student_candidates(db, mentor, limit=10)

        assert mentor_results[0][0].id == mentor.id
        assert student_results[0][0].id == student.id
        assert mentor_results[0][1].score == student_results[0][1].score


def test_higher_academic_fit_is_prioritized_before_same_college() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        organization = Tenant(slug="college-priority-test", name="College Priority Test")
        db.add(organization); db.flush()
        student_role = Role(tenant_id=organization.id, code="student", name_zh="Student", name_en="Student")
        mentor_role = Role(tenant_id=organization.id, code="mentor", name_zh="Mentor", name_en="Mentor")
        student = User(tenant_id=organization.id, username="TEST_S1", full_name="Student", password_hash="hash")
        same_college = User(tenant_id=organization.id, username="TEST_T1", full_name="Same College", password_hash="hash")
        higher_score = User(tenant_id=organization.id, username="TEST_T2", full_name="Other College", password_hash="hash")
        student.roles.append(student_role)
        same_college.roles.append(mentor_role)
        higher_score.roles.append(mentor_role)
        db.add_all([student, same_college, higher_score]); db.flush()
        db.add_all([
            StudentProfile(user_id=student.id, institution_abbr="TEST", profile_completed_at=datetime.now(timezone.utc), university="AcademicNexus University", department="College of Computing", research_interests=["NLP"], skills=["Python"]),
            MentorProfile(user_id=same_college.id, institution_abbr="TEST", profile_completed_at=datetime.now(timezone.utc), university="AcademicNexus University", department="College of Computing", research_directions=["History"], representative_papers=[]),
            MentorProfile(user_id=higher_score.id, institution_abbr="TEST", profile_completed_at=datetime.now(timezone.utc), university="AcademicNexus University", department="College of Design", research_directions=["NLP"], representative_papers=[]),
        ])
        db.commit(); db.refresh(student)

        results = mentor_recommendations(db, student, limit=10)

        assert [item[0].id for item in results] == [higher_score.id, same_college.id]


def test_matching_filters_before_external_calls_and_paginates(monkeypatch):
    from app.api.v1.endpoints.matching import recommend_mentors
    from app.services import ranking
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine, autoflush=False, expire_on_commit=False) as db:
        organization = Tenant(slug="scope", name="Scope")
        other = Tenant(slug="other", name="Other")
        db.add_all([organization, other]); db.flush()
        mentor_role = Role(tenant_id=organization.id, code="mentor", name_zh="Mentor", name_en="Mentor")
        source = User(tenant_id=organization.id, username="S1", full_name="Student", password_hash="hash")
        source.student_profile = StudentProfile(institution_abbr="TEST", research_interests=["language"])
        db.add(source)
        for n, (institution, active, complete, tenant_id) in enumerate([
            ("TEST", True, True, organization.id), ("TEST", True, True, organization.id),
            ("OTHER", True, True, organization.id), (None, True, True, organization.id),
            ("TEST", False, True, organization.id), ("TEST", True, False, organization.id),
            ("TEST", True, True, other.id),
        ]):
            target = User(tenant_id=tenant_id, username=f"M{n}", full_name=f"Mentor {n}", password_hash="hash", is_active=active)
            target.roles.append(mentor_role)
            target.mentor_profile = MentorProfile(institution_abbr=institution, research_directions=[f"research{n}"],
                profile_completed_at=datetime.now(timezone.utc) if complete else None)
            db.add(target)
        db.commit()
        def rank(db, tenant_id, query, candidates):
            assert len(candidates) == 2
            assert {item.text for item in candidates} == {"research0", "research1"}
            return ranking.RankingResult({item.id: 50 for item in candidates}, "hybrid")
        monkeypatch.setattr(ranking, "rank", rank)
        first = recommend_mentors(db, source, limit=1, offset=0)
        second = recommend_mentors(db, source, limit=1, offset=1)
        assert first.total == second.total == 2
        assert first.ranking_mode == "hybrid"
        assert first.items[0].user_id != second.items[0].user_id
        assert not first.items[0].same_college
