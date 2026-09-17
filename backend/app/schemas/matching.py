"""Read models for the explainable academic-profile matching API."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


MatchFactorCode = Literal["research_alignment", "skills_alignment", "development_alignment"]


class MatchFactorResponse(BaseModel):
    """A visible component of a recommendation score, never a hidden black box."""

    code: MatchFactorCode
    score: int = Field(ge=0, le=100)
    shared_terms: list[str] = Field(default_factory=list)


class MatchedMentorResponse(BaseModel):
    user_id: UUID
    username: str
    full_name: str
    university: str | None
    department: str | None
    same_college: bool
    title: str | None
    research_directions: list[str] = Field(default_factory=list)
    representative_papers: list[str] = Field(default_factory=list)
    research_projects: str | None
    mentoring_style: str | None
    match_score: int = Field(ge=0, le=100)
    factors: list[MatchFactorResponse]


class MatchedStudentResponse(BaseModel):
    user_id: UUID
    username: str
    full_name: str
    university: str | None
    department: str | None
    same_college: bool
    major: str | None
    grade: str | None
    research_interests: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    academic_performance: str | None
    academic_goals: str | None
    research_experience: str | None
    match_score: int = Field(ge=0, le=100)
    factors: list[MatchFactorResponse]


class MentorRecommendationListResponse(BaseModel):
    algorithm_version: str
    ranking_mode: Literal["local", "semantic", "hybrid"] = "local"
    total: int
    items: list[MatchedMentorResponse]


class StudentCandidateListResponse(BaseModel):
    algorithm_version: str
    ranking_mode: Literal["local", "semantic", "hybrid"] = "local"
    total: int
    items: list[MatchedStudentResponse]
