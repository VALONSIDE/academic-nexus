"""Role-specific, explainable mentor matching endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import DbSession, require_roles
from app.models.user import User
from app.schemas.matching import (
    MatchFactorResponse,
    MatchedMentorResponse,
    MatchedStudentResponse,
    MentorRecommendationListResponse,
    StudentCandidateListResponse,
)
from app.services.matching import ALGORITHM_VERSION, mentor_recommendations, student_candidates


router = APIRouter(prefix="/matching", tags=["Mentor matching / 导师匹配"])


def _factors(score) -> list[MatchFactorResponse]:
    return [MatchFactorResponse(code=item.code, score=item.score, shared_terms=item.shared_terms) for item in score.factors]


@router.get("/mentors", response_model=MentorRecommendationListResponse, summary="Recommend mentors / 推荐导师")
def recommend_mentors(
    db: DbSession,
    student: User = Depends(require_roles("student")),
    limit: int | None = Query(default=None, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
) -> MentorRecommendationListResponse:
    student = db.scalar(
        select(User).options(selectinload(User.student_profile)).where(User.id == student.id)
    )
    if student is None or student.student_profile is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"code": "portrait_required"})
    matches = mentor_recommendations(db, student)
    db.commit()
    total = len(matches)
    mode = matches[0][1].ranking_mode if matches else "local"
    matches = matches[offset:offset + limit] if limit is not None else matches[offset:]
    return MentorRecommendationListResponse(
        algorithm_version=ALGORITHM_VERSION,
        total=total,
        ranking_mode=mode,
        items=[
            MatchedMentorResponse(
                user_id=mentor.id,
                username=mentor.username or "",
                full_name=mentor.full_name,
                university=mentor.mentor_profile.university,
                department=mentor.mentor_profile.department,
                same_college=bool(student.student_profile.department and mentor.mentor_profile.department == student.student_profile.department),
                title=mentor.mentor_profile.title,
                research_directions=mentor.mentor_profile.research_directions or [],
                representative_papers=mentor.mentor_profile.representative_papers or [],
                research_projects=mentor.mentor_profile.research_projects,
                mentoring_style=mentor.mentor_profile.mentoring_style,
                match_score=score.score,
                factors=_factors(score),
            )
            for mentor, score in matches
        ],
    )


@router.get("/students", response_model=StudentCandidateListResponse, summary="Recommend students / 推荐学生")
def recommend_students(
    db: DbSession,
    mentor: User = Depends(require_roles("mentor")),
    limit: int | None = Query(default=None, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
) -> StudentCandidateListResponse:
    mentor = db.scalar(
        select(User).options(selectinload(User.mentor_profile)).where(User.id == mentor.id)
    )
    if mentor is None or mentor.mentor_profile is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"code": "portrait_required"})
    matches = student_candidates(db, mentor)
    db.commit()
    total = len(matches)
    mode = matches[0][1].ranking_mode if matches else "local"
    matches = matches[offset:offset + limit] if limit is not None else matches[offset:]
    return StudentCandidateListResponse(
        algorithm_version=ALGORITHM_VERSION,
        total=total,
        ranking_mode=mode,
        items=[
            MatchedStudentResponse(
                user_id=student.id,
                username=student.username or "",
                full_name=student.full_name,
                university=student.student_profile.university,
                department=student.student_profile.department,
                same_college=bool(mentor.mentor_profile.department and student.student_profile.department == mentor.mentor_profile.department),
                major=student.student_profile.major,
                grade=student.student_profile.grade,
                research_interests=student.student_profile.research_interests or [],
                skills=student.student_profile.skills or [],
                academic_performance=student.student_profile.academic_performance,
                academic_goals=student.student_profile.academic_goals,
                research_experience=student.student_profile.research_experience,
                match_score=score.score,
                factors=_factors(score),
            )
            for student, score in matches
        ],
    )
