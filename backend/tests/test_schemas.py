import pytest
from pydantic import ValidationError

from app.schemas.auth import ActivationRequest
from app.schemas.profiles import MentorAcademicProfilePayload, StudentAcademicProfilePayload


def test_activation_requires_a_strong_password() -> None:
    with pytest.raises(ValidationError):
        ActivationRequest(
            username="CUC_S20240001",
            full_name="Test Student",
            academic_id="20240001",
            access_key="1234-ABCD-5678-9012",
            password="onlylowercase12",
        )


def test_activation_accepts_a_valid_receipt_shape() -> None:
    request = ActivationRequest(
        username="cuc_s20240001",
        full_name="Test Student",
        academic_id="20240001",
        access_key="1234-abcd-5678-9012",
        password="AcademicNexus2026",
    )
    assert request.username == "CUC_S20240001"
    assert request.access_key == "1234-ABCD-5678-9012"


def test_student_portrait_requires_complete_fields_and_normalizes_tags() -> None:
    profile = StudentAcademicProfilePayload(
        research_interests=["AI", "ai", "教育技术"],
        skills=["Python", "Research"],
        academic_performance="GPA 3.8/4.0",
        academic_goals="Apply for a research master's program.",
        research_experience="Completed a literature review project.",
    )
    assert profile.research_interests == ["AI", "教育技术"]


def test_mentor_portrait_requires_representative_papers() -> None:
    with pytest.raises(ValidationError):
        MentorAcademicProfilePayload(
            research_directions=["Natural language processing"],
            representative_papers=[],
            research_projects="National research project",
            mentoring_style="Weekly meetings and milestone feedback.",
        )
