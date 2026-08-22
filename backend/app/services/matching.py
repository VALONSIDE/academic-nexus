"""Cold-start-safe, explainable matching built from academic portraits.

The first production algorithm deliberately relies on explicit portrait tags and
transparent text signals.  It avoids pretending that a sparse pilot dataset is
a trained model, while keeping this service boundary ready for embeddings and a
vector store in a later iteration.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.user import MentorProfile, StudentProfile, User


ALGORITHM_VERSION = "profile-hybrid-v1"
_TERM_SPLIT = re.compile(r"[,，;；、|/\n\r]+")
_WORD_PATTERN = re.compile(r"[a-z0-9+#._-]+", re.IGNORECASE)


@dataclass(frozen=True)
class MatchFactor:
    code: str
    score: int
    shared_terms: list[str]


@dataclass(frozen=True)
class ScoredMatch:
    score: int
    factors: list[MatchFactor]


def _phrases(values: list[str] | None, *texts: str | None) -> set[str]:
    """Normalize both tag fields and free text into comparable, stable phrases."""
    raw_values = list(values or []) + [text for text in texts if text]
    phrases: set[str] = set()
    for raw in raw_values:
        for phrase in _TERM_SPLIT.split(raw):
            normalized = " ".join(phrase.casefold().split())
            if normalized:
                phrases.add(normalized)
    return phrases


def _term_similarity(left: set[str], right: set[str]) -> tuple[int, list[str]]:
    """Compare tag phrases and tolerate containment such as NLP vs Chinese NLP."""
    if not left or not right:
        return 0, []
    shared = sorted(
        {
            shorter
            for first in left
            for second in right
            if (shorter := first if len(first) <= len(second) else second)
            and (first == second or (len(shorter) >= 2 and shorter in (second if shorter == first else first)))
        }
    )
    phrase_score = len(shared) / max(len(left), len(right))
    left_words = {word for phrase in left for word in _WORD_PATTERN.findall(phrase) if len(word) > 1}
    right_words = {word for phrase in right for word in _WORD_PATTERN.findall(phrase) if len(word) > 1}
    word_union = left_words | right_words
    word_score = len(left_words & right_words) / len(word_union) if word_union else 0
    return round(min(1.0, phrase_score * 0.8 + word_score * 0.2) * 100), shared[:5]


def score_student_to_mentor(student: StudentProfile, mentor: MentorProfile) -> ScoredMatch:
    """Return a 0-100 score and the factors shown to the platform user."""
    research_score, research_terms = _term_similarity(
        _phrases(student.research_interests),
        _phrases(mentor.research_directions),
    )
    skills_score, skills_terms = _term_similarity(
        _phrases(student.skills),
        _phrases(
            mentor.research_directions,
            mentor.research_projects,
            "; ".join(mentor.representative_papers or []),
        ),
    )
    development_score, development_terms = _term_similarity(
        _phrases(None, student.academic_goals, student.research_experience),
        _phrases(None, mentor.research_projects, mentor.mentoring_style),
    )
    factors = [
        MatchFactor("research_alignment", research_score, research_terms),
        MatchFactor("skills_alignment", skills_score, skills_terms),
        MatchFactor("development_alignment", development_score, development_terms),
    ]
    score = round(research_score * 0.7 + skills_score * 0.15 + development_score * 0.15)
    return ScoredMatch(score=score, factors=factors)


def _active_users_with_role(db: Session, *, tenant_id, role: str) -> list[User]:
    statement = (
        select(User)
        .options(selectinload(User.student_profile), selectinload(User.mentor_profile))
        .where(User.tenant_id == tenant_id, User.is_active.is_(True), User.roles.any(code=role))
    )
    return list(db.scalars(statement).unique().all())


def mentor_recommendations(db: Session, student_user: User, *, limit: int | None = None) -> list[tuple[User, ScoredMatch]]:
    if student_user.student_profile is None:
        return []
    recommendations = [
        (mentor_user, score_student_to_mentor(student_user.student_profile, mentor_user.mentor_profile))
        for mentor_user in _active_users_with_role(db, tenant_id=student_user.tenant_id, role="mentor")
        if mentor_user.mentor_profile is not None
        and mentor_user.mentor_profile.university == student_user.student_profile.university
    ]
    ordered = sorted(
        recommendations,
        key=lambda item: (
            item[0].mentor_profile.department != student_user.student_profile.department,
            -item[1].score,
            item[0].full_name,
            item[0].username or "",
        ),
    )
    return ordered[:limit] if limit is not None else ordered


def student_candidates(db: Session, mentor_user: User, *, limit: int | None = None) -> list[tuple[User, ScoredMatch]]:
    if mentor_user.mentor_profile is None:
        return []
    candidates = [
        (student_user, score_student_to_mentor(student_user.student_profile, mentor_user.mentor_profile))
        for student_user in _active_users_with_role(db, tenant_id=mentor_user.tenant_id, role="student")
        if student_user.student_profile is not None
        and student_user.student_profile.university == mentor_user.mentor_profile.university
    ]
    ordered = sorted(
        candidates,
        key=lambda item: (
            item[0].student_profile.department != mentor_user.mentor_profile.department,
            -item[1].score,
            item[0].full_name,
            item[0].username or "",
        ),
    )
    return ordered[:limit] if limit is not None else ordered
