"""Academic matching with semantic ranking and explainable local fallback."""

from __future__ import annotations

import re
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.user import MentorProfile, StudentProfile, User
from app.services import ranking


ALGORITHM_VERSION = ranking.ALGORITHM_VERSION
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
    ranking_mode: str = "local"


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


def _active_users_with_role(db: Session, *, tenant_id, role: str, institution: str) -> list[User]:
    profile_type = MentorProfile if role == "mentor" else StudentProfile
    statement = (
        select(User)
        .join(profile_type, profile_type.user_id == User.id)
        .options(selectinload(User.student_profile), selectinload(User.mentor_profile))
        .where(User.tenant_id == tenant_id, User.is_active.is_(True), User.roles.any(code=role))
        .where(profile_type.institution_abbr == institution, profile_type.profile_completed_at.is_not(None))
    )
    return list(db.scalars(statement).unique().all())


def _recommend(db, source, *, source_role, target_role, limit):
    profile = getattr(source, f"{source_role}_profile")
    if profile is None or not profile.institution_abbr:
        return []
    matches = []
    candidates = []
    for target in _active_users_with_role(db, tenant_id=source.tenant_id, role=target_role, institution=profile.institution_abbr):
        target_profile = getattr(target, f"{target_role}_profile")
        if (target_profile is None or target_profile.institution_abbr != profile.institution_abbr
                or target_profile.profile_completed_at is None or target.id == source.id):
            continue
        student, mentor = (profile, target_profile) if source_role == "student" else (target_profile, profile)
        score = score_student_to_mentor(student, mentor)
        matches.append((target, score))
        candidates.append(ranking.Candidate(str(target.id), ranking.academic_text(target_profile, target), score.score))
    result = ranking.rank(db, source.tenant_id, ranking.academic_text(profile, source), candidates)
    ordered = [(target, ScoredMatch(result.scores[str(target.id)], score.factors, result.mode)) for target, score in matches]
    # Academic fit first; a real, non-empty shared department only breaks ties.
    ordered.sort(key=lambda item: (-item[1].score,
        not (profile.department and getattr(item[0], f"{target_role}_profile").department == profile.department), str(item[0].id)))
    return ordered[:limit] if limit is not None else ordered


def mentor_recommendations(db: Session, student_user: User, *, limit: int | None = None) -> list[tuple[User, ScoredMatch]]:
    return _recommend(db, student_user, source_role="student", target_role="mentor", limit=limit)


def student_candidates(db: Session, mentor_user: User, *, limit: int | None = None) -> list[tuple[User, ScoredMatch]]:
    return _recommend(db, mentor_user, source_role="mentor", target_role="student", limit=limit)
