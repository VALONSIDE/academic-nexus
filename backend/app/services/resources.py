"""Storage, quota, catalog, and cold-start recommendation helpers for resources."""

from __future__ import annotations

import os
import re
import uuid
from dataclasses import dataclass
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.models.resource import Book, Course, MentorResourceQuota, Paper, Resource
from app.models.user import StudentProfile, User


MEGABYTE = 1024 * 1024
_SPLIT = re.compile(r"[,，;；、|/\n\r]+")
_EXTENSIONS = {".pdf", ".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx", ".txt", ".md", ".zip"}


class ResourceError(RuntimeError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class StagedFile:
    temporary_path: Path
    size_bytes: int
    original_name: str
    content_type: str | None
    extension: str


def parse_terms(value: str | None) -> list[str]:
    if not value:
        return []
    terms: list[str] = []
    for item in _SPLIT.split(value):
        normalized = " ".join(item.strip().split())
        if normalized and normalized not in terms:
            terms.append(normalized[:120])
    return terms[:20]


def storage_root() -> Path:
    root = Path(get_settings().resource_storage_path).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _storage_path(key: str) -> Path:
    root = storage_root()
    candidate = (root / key).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as error:
        raise ResourceError("invalid_storage_key") from error
    return candidate


async def stage_upload(upload: UploadFile) -> StagedFile | None:
    if not upload.filename:
        return None
    original_name = Path(upload.filename).name
    extension = Path(original_name).suffix.lower()
    if extension not in _EXTENSIONS:
        raise ResourceError("unsupported_file_type")
    root = storage_root()
    temporary_path = root / f".upload-{uuid.uuid4().hex}.tmp"
    limit = get_settings().resource_max_upload_mb * MEGABYTE
    size = 0
    try:
        with temporary_path.open("wb") as stream:
            while chunk := await upload.read(1024 * 1024):
                size += len(chunk)
                if size > limit:
                    raise ResourceError("file_too_large")
                stream.write(chunk)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise
    finally:
        await upload.close()
    return StagedFile(temporary_path, size, original_name[:255], upload.content_type, extension)


def _quota(db: Session, mentor_id, *, lock: bool = False) -> MentorResourceQuota:
    statement = select(MentorResourceQuota).where(MentorResourceQuota.user_id == mentor_id)
    if lock:
        statement = statement.with_for_update()
    quota = db.scalar(statement)
    if quota is not None:
        return quota
    quota = MentorResourceQuota(
        user_id=mentor_id,
        quota_bytes=get_settings().mentor_resource_default_quota_mb * MEGABYTE,
        used_bytes=0,
    )
    db.add(quota)
    db.flush()
    return quota


def quota_snapshot(db: Session, mentor_id) -> MentorResourceQuota:
    return _quota(db, mentor_id)


def reserve_file_bytes(db: Session, mentor_id, size_bytes: int) -> MentorResourceQuota:
    quota = _quota(db, mentor_id, lock=True)
    if quota.used_bytes + size_bytes > quota.quota_bytes:
        raise ResourceError("resource_quota_exceeded")
    quota.used_bytes += size_bytes
    return quota


def update_quota(db: Session, mentor_id, quota_mb: int) -> MentorResourceQuota:
    quota = _quota(db, mentor_id, lock=True)
    requested = quota_mb * MEGABYTE
    if requested < quota.used_bytes:
        raise ResourceError("quota_below_used_storage")
    quota.quota_bytes = requested
    db.commit()
    db.refresh(quota)
    return quota


def add_specialization(resource: Resource, *, resource_type: str, form: dict[str, str | int | None]) -> None:
    if resource_type == "course":
        resource.course = Course(provider=_text(form.get("provider"), 160), level=_text(form.get("level"), 80), duration=_text(form.get("duration"), 80))
    elif resource_type == "paper":
        resource.paper = Paper(
            authors=_text(form.get("authors"), 800),
            publication=_text(form.get("publication"), 400),
            doi=_text(form.get("doi"), 200),
            publication_year=_year(form.get("publication_year")),
        )
    else:
        resource.book = Book(
            authors=_text(form.get("authors"), 800),
            publisher=_text(form.get("publisher"), 400),
            isbn=_text(form.get("isbn"), 64),
            publication_year=_year(form.get("publication_year")),
        )


def _text(value: str | int | None, maximum: int) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized[:maximum] or None


def _year(value: str | int | None) -> int | None:
    if value in (None, ""):
        return None
    try:
        year = int(value)
    except (TypeError, ValueError) as error:
        raise ResourceError("invalid_publication_year") from error
    if year < 1000 or year > 2100:
        raise ResourceError("invalid_publication_year")
    return year


def finalize_staged_file(staged: StagedFile, *, tenant_id, mentor_id) -> str:
    key = f"{tenant_id}/{mentor_id}/{uuid.uuid4().hex}{staged.extension}"
    target = _storage_path(key)
    target.parent.mkdir(parents=True, exist_ok=True)
    os.replace(staged.temporary_path, target)
    return key


def discard_staged_file(staged: StagedFile | None) -> None:
    if staged is not None:
        staged.temporary_path.unlink(missing_ok=True)


def file_path(resource: Resource) -> Path | None:
    return _storage_path(resource.file_storage_key) if resource.file_storage_key else None


def delete_stored_file(resource: Resource) -> None:
    target = file_path(resource)
    if target is not None:
        target.unlink(missing_ok=True)


def _resource_statement(*, tenant_id, owner_user_id=None, resource_type: str | None = None, search: str = ""):
    statement = select(Resource).options(selectinload(Resource.course), selectinload(Resource.paper), selectinload(Resource.book))
    statement = statement.where(Resource.tenant_id == tenant_id, Resource.is_published.is_(True))
    if owner_user_id is not None:
        statement = statement.where(Resource.owner_user_id == owner_user_id)
    if resource_type:
        statement = statement.where(Resource.resource_type == resource_type)
    if search.strip():
        pattern = f"%{search.strip()}%"
        statement = statement.where(or_(Resource.title.ilike(pattern), Resource.description.ilike(pattern)))
    return statement.order_by(Resource.created_at.desc())


def list_resources(db: Session, *, tenant_id, owner_user_id=None, resource_type: str | None = None, search: str = "") -> list[Resource]:
    return list(db.scalars(_resource_statement(tenant_id=tenant_id, owner_user_id=owner_user_id, resource_type=resource_type, search=search)).all())


def get_resource(db: Session, *, tenant_id, resource_id) -> Resource | None:
    return db.scalar(
        select(Resource)
        .options(selectinload(Resource.course), selectinload(Resource.paper), selectinload(Resource.book))
        .where(Resource.id == resource_id, Resource.tenant_id == tenant_id)
    )


def metadata(resource: Resource) -> dict[str, str | int | None]:
    if resource.course is not None:
        return {"provider": resource.course.provider, "level": resource.course.level, "duration": resource.course.duration}
    if resource.paper is not None:
        return {"authors": resource.paper.authors, "publication": resource.paper.publication, "doi": resource.paper.doi, "publication_year": resource.paper.publication_year}
    if resource.book is not None:
        return {"authors": resource.book.authors, "publisher": resource.book.publisher, "isbn": resource.book.isbn, "publication_year": resource.book.publication_year}
    return {}


def owners_by_id(db: Session, resources: list[Resource]) -> dict[object, str]:
    owner_ids = {resource.owner_user_id for resource in resources}
    if not owner_ids:
        return {}
    return dict(db.execute(select(User.id, User.full_name).where(User.id.in_(owner_ids))).all())


def recommendation_score(profile: StudentProfile, resource: Resource) -> int:
    student_terms = {term.casefold() for term in (profile.research_interests or []) + (profile.skills or []) + parse_terms(profile.academic_goals)}
    resource_terms = {term.casefold() for term in resource.topics + resource.tags + parse_terms(resource.title) + parse_terms(resource.description)}
    if not student_terms or not resource_terms:
        return 0
    shared = {
        short
        for first in student_terms
        for second in resource_terms
        if (short := first if len(first) <= len(second) else second) and (first == second or (len(short) >= 2 and short in (second if short == first else first)))
    }
    return round(min(1, len(shared) / max(len(student_terms), len(resource_terms))) * 100)


def recommended_resources(db: Session, student: User, *, limit: int) -> list[tuple[Resource, int]]:
    if student.student_profile is None:
        return []
    resources = list_resources(db, tenant_id=student.tenant_id)
    ranked = [(resource, recommendation_score(student.student_profile, resource)) for resource in resources]
    return sorted(ranked, key=lambda item: (-item[1], item[0].title.casefold()))[:limit]
