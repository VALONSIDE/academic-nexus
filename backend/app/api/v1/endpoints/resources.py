"""Learning-resource library, mentor uploads, and administrator storage controls."""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import HttpUrl, TypeAdapter, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DbSession, require_roles, require_super_admin
from app.models.resource import MentorResourceQuota, Resource
from app.models.user import User
from app.schemas.resource import (
    AdminResourceQuotaListResponse,
    AdminResourceQuotaUpdateRequest,
    AdminResourceQuotaUserResponse,
    MentorResourceQuotaResponse,
    ResourceListResponse,
    ResourceResponse,
    ResourceType,
)
from app.services import resources as resource_service


router = APIRouter(prefix="/resources", tags=["Learning resources / 学习资源"])
mentor_router = APIRouter(prefix="/mentor/resources", tags=["Mentor resources / 导师资源"])
admin_router = APIRouter(prefix="/admin/resource-quotas", tags=["Resource quota administration / 资源配额管理"])
logger = logging.getLogger(__name__)
_http_url = TypeAdapter(HttpUrl)


def _quota_response(quota: MentorResourceQuota) -> MentorResourceQuotaResponse:
    return MentorResourceQuotaResponse(
        quota_bytes=quota.quota_bytes,
        used_bytes=quota.used_bytes,
        remaining_bytes=max(0, quota.quota_bytes - quota.used_bytes),
    )


def _serialize(resource: Resource, owner_names: dict[object, str], *, recommendation_score: int | None = None) -> ResourceResponse:
    return ResourceResponse(
        id=resource.id,
        resource_type=resource.resource_type,
        title=resource.title,
        description=resource.description,
        topics=resource.topics or [],
        tags=resource.tags or [],
        external_url=resource.external_url,
        file_original_name=resource.file_original_name,
        file_size_bytes=resource.file_size_bytes,
        download_url=f"/api/v1/resources/{resource.id}/download" if resource.file_storage_key else None,
        owner_name=owner_names.get(resource.owner_user_id, ""),
        created_at=resource.created_at,
        metadata=resource_service.metadata(resource),
        recommendation_score=recommendation_score,
    )


def _resource_error(error: resource_service.ResourceError) -> HTTPException:
    http_status = status.HTTP_409_CONFLICT if error.code in {"resource_quota_exceeded", "quota_below_used_storage"} else status.HTTP_400_BAD_REQUEST
    return HTTPException(status_code=http_status, detail={"code": error.code})


def _validate_url(value: str) -> str | None:
    normalized = value.strip()
    if not normalized:
        return None
    try:
        parsed = _http_url.validate_python(normalized)
    except ValidationError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"code": "invalid_resource_url"})
    if len(normalized) > 2048 or parsed.username or parsed.password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"code": "invalid_resource_url"})
    return str(parsed)


@router.get("", response_model=ResourceListResponse, summary="List resource library / 查询资源库")
def list_resource_library(
    current_user: CurrentUser,
    db: DbSession,
    resource_type: ResourceType | None = Query(default=None),
    search: str = Query(default="", max_length=120),
) -> ResourceListResponse:
    resources = resource_service.list_resources(db, tenant_id=current_user.tenant_id, resource_type=resource_type, search=search)
    owners = resource_service.owners_by_id(db, resources)
    return ResourceListResponse(items=[_serialize(resource, owners) for resource in resources], total=len(resources))


@router.get("/recommended", response_model=ResourceListResponse, summary="Recommend resources to a student / 推荐学习资源")
def recommend_resources(
    db: DbSession,
    student: User = Depends(require_roles("student")),
    limit: int = Query(default=6, ge=1, le=30),
) -> ResourceListResponse:
    student = db.scalar(select(User).options(selectinload(User.student_profile)).where(User.id == student.id))
    if student is None or student.student_profile is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"code": "portrait_required"})
    ranked = resource_service.recommended_resources(db, student, limit=limit)
    db.commit()
    owners = resource_service.owners_by_id(db, [resource for resource, _ in ranked])
    return ResourceListResponse(
        ranking_mode=db.info.get("resource_ranking_mode", "local"),
        items=[_serialize(resource, owners, recommendation_score=score) for resource, score in ranked],
        total=len(ranked),
    )


@router.get("/{resource_id}/download", summary="Download a resource file / 下载资源文件")
def download_resource(resource_id: UUID, current_user: CurrentUser, db: DbSession) -> FileResponse:
    resource = resource_service.get_resource(db, tenant_id=current_user.tenant_id, resource_id=resource_id)
    if resource is None or not resource.is_published or not resource.file_storage_key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "resource_not_found"})
    try:
        path = resource_service.file_path(resource)
    except resource_service.ResourceError as error:
        raise _resource_error(error) from error
    if path is None or not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "resource_file_not_found"})
    return FileResponse(path, media_type="application/octet-stream", filename=resource.file_original_name or path.name,
                        headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})


@mentor_router.get("/quota", response_model=MentorResourceQuotaResponse, summary="Read own resource storage quota / 获取资源存储配额")
def read_mentor_quota(db: DbSession, mentor: User = Depends(require_roles("mentor"))) -> MentorResourceQuotaResponse:
    quota = resource_service.quota_snapshot(db, mentor.id)
    db.commit()
    return _quota_response(quota)


@mentor_router.get("", response_model=ResourceListResponse, summary="List own resources / 查询我的资源")
def list_own_resources(db: DbSession, mentor: User = Depends(require_roles("mentor"))) -> ResourceListResponse:
    resources = resource_service.list_resources(db, tenant_id=mentor.tenant_id, owner_user_id=mentor.id)
    return ResourceListResponse(items=[_serialize(resource, {mentor.id: mentor.full_name}) for resource in resources], total=len(resources))


@mentor_router.post("", response_model=ResourceResponse, status_code=status.HTTP_201_CREATED, summary="Upload a learning resource / 上传学习资源")
async def create_resource(
    resource_type: Annotated[ResourceType, Form()],
    title: Annotated[str, Form(min_length=2, max_length=240)],
    db: DbSession,
    mentor: User = Depends(require_roles("mentor")),
    description: Annotated[str, Form(max_length=5000)] = "",
    topics: Annotated[str, Form(max_length=2000)] = "",
    tags: Annotated[str, Form(max_length=2000)] = "",
    external_url: Annotated[str, Form(max_length=2048)] = "",
    provider: Annotated[str, Form(max_length=160)] = "",
    level: Annotated[str, Form(max_length=80)] = "",
    duration: Annotated[str, Form(max_length=80)] = "",
    duration_hours: Annotated[str, Form(max_length=4)] = "",
    duration_minutes: Annotated[str, Form(max_length=2)] = "",
    authors: Annotated[str, Form(max_length=800)] = "",
    publication: Annotated[str, Form(max_length=400)] = "",
    doi: Annotated[str, Form(max_length=200)] = "",
    publisher: Annotated[str, Form(max_length=400)] = "",
    isbn: Annotated[str, Form(max_length=64)] = "",
    publication_year: Annotated[str, Form(max_length=4)] = "",
    file: UploadFile | None = File(default=None),
) -> ResourceResponse:
    staged: resource_service.StagedFile | None = None
    persisted_key: str | None = None
    committed = False
    try:
        if len(title.strip()) < 2:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Title must contain at least two non-space characters / 标题至少包含两个非空白字符")
        staged = await resource_service.stage_upload(file) if file is not None else None
        url = _validate_url(external_url)
        if staged is None and url is None:
            raise resource_service.ResourceError("resource_location_required")
        if staged is not None:
            resource_service.reserve_file_bytes(db, mentor.id, staged.size_bytes)
        resource = Resource(
            tenant_id=mentor.tenant_id,
            owner_user_id=mentor.id,
            resource_type=resource_type,
            title=title.strip(),
            description=description.strip(),
            topics=resource_service.parse_terms(topics),
            tags=resource_service.parse_terms(tags),
            external_url=url,
            file_original_name=staged.original_name if staged else None,
            file_content_type=staged.content_type if staged else None,
            file_size_bytes=staged.size_bytes if staged else 0,
        )
        db.add(resource)
        resource_service.add_specialization(
            resource,
            resource_type=resource_type,
            form={
                "provider": provider,
                "level": level,
                "duration": (
                    resource_service.course_duration_from_parts(duration_hours, duration_minutes)
                    if resource_type == "course" and (duration_hours.strip() or duration_minutes.strip())
                    else duration
                ),
                "authors": authors,
                "publication": publication,
                "doi": doi,
                "publisher": publisher,
                "isbn": isbn,
                "publication_year": publication_year,
            },
        )
        db.flush()
        if staged is not None:
            persisted_key = resource_service.finalize_staged_file(staged, tenant_id=mentor.tenant_id, mentor_id=mentor.id)
            resource.file_storage_key = persisted_key
        db.commit()
        committed = True
        db.refresh(resource)
        return _serialize(resource, {mentor.id: mentor.full_name})
    except resource_service.ResourceError as error:
        db.rollback()
        if persisted_key and not committed:
            try:
                resource_service._storage_path(persisted_key).unlink(missing_ok=True)
            except resource_service.ResourceError:
                pass
        raise _resource_error(error) from error
    except Exception:
        db.rollback()
        if persisted_key and not committed:
            try:
                resource_service._storage_path(persisted_key).unlink(missing_ok=True)
            except resource_service.ResourceError:
                pass
        raise
    finally:
        resource_service.discard_staged_file(staged)


@mentor_router.delete("/{resource_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete own resource / 删除我的资源")
def delete_resource(resource_id: UUID, db: DbSession, mentor: User = Depends(require_roles("mentor"))) -> None:
    resource = resource_service.get_resource(db, tenant_id=mentor.tenant_id, resource_id=resource_id, lock=True)
    if resource is None or resource.owner_user_id != mentor.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "resource_not_found"})
    file_size = resource.file_size_bytes
    try:
        path = resource_service.file_path(resource)
    except resource_service.ResourceError as error:
        raise _resource_error(error) from error
    resource_service.release_file_bytes(db, mentor.id, file_size)
    db.delete(resource)
    db.commit()
    if path is not None:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            logger.exception("Unable to remove file for deleted resource %s", resource_id)


@admin_router.get("", response_model=AdminResourceQuotaListResponse, summary="List mentor resource quotas / 查询导师资源配额")
def list_resource_quotas(
    db: DbSession,
    admin: User = Depends(require_super_admin),
    search: str = Query(default="", max_length=100),
) -> AdminResourceQuotaListResponse:
    statement = select(User).options(selectinload(User.roles)).where(User.tenant_id == admin.tenant_id, User.roles.any(code="mentor"))
    if search.strip():
        pattern = f"%{search.strip()}%"
        statement = statement.where(User.username.ilike(pattern) | User.full_name.ilike(pattern))
    mentors = db.scalars(statement.order_by(User.created_at.desc())).unique().all()
    items: list[AdminResourceQuotaUserResponse] = []
    for mentor in mentors:
        quota = resource_service.quota_snapshot(db, mentor.id)
        items.append(
            AdminResourceQuotaUserResponse(
                user_id=mentor.id,
                username=mentor.username or "",
                full_name=mentor.full_name,
                **_quota_response(quota).model_dump(),
            )
        )
    db.commit()
    return AdminResourceQuotaListResponse(items=items, total=len(items))


@admin_router.patch("/{user_id}", response_model=MentorResourceQuotaResponse, summary="Update mentor resource quota / 更新导师资源配额")
def update_resource_quota(
    user_id: UUID,
    payload: AdminResourceQuotaUpdateRequest,
    db: DbSession,
    admin: User = Depends(require_super_admin),
) -> MentorResourceQuotaResponse:
    mentor = db.scalar(select(User).options(selectinload(User.roles)).where(User.id == user_id, User.tenant_id == admin.tenant_id))
    if mentor is None or not any(role.code == "mentor" for role in mentor.roles):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "mentor_not_found"})
    try:
        quota = resource_service.update_quota(db, mentor.id, payload.quota_mb)
    except resource_service.ResourceError as error:
        raise _resource_error(error) from error
    return _quota_response(quota)
