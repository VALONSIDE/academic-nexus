from typing import Annotated

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import Response
from sqlalchemy import or_, select
from app.api.deps import DbSession, require_roles
from app.models.pre_registration import PreRegistration
from app.models.user import User
from app.schemas.pre_registration import PreRegistrationAdminResponse, PreRegistrationBulkDeleteRequest, PreRegistrationListResponse
from app.services.pre_registration_import import (
    PreRegistrationImportError,
    build_import_template,
    build_receipt_workbook,
    import_pre_registrations,
)

router = APIRouter(prefix="/admin/pre-registrations", tags=["Partner pre-registration / 合作院校预注册"])
XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
MAX_IMPORT_SIZE = 10 * 1024 * 1024


def _pre_registration_response(item: PreRegistration) -> PreRegistrationAdminResponse:
    return PreRegistrationAdminResponse(
        id=item.id,
        batch_id=item.batch_id,
        username=item.username,
        role_code=item.role_code,
        full_name=item.full_name,
        academic_id=item.academic_id,
        institution_abbr=item.institution_abbr,
        institution_name_zh=item.institution_name_zh,
        college_name_zh=item.college_name_zh,
        status=item.status,
        created_at=item.created_at,
        activated_at=item.activated_at,
    )


def _delete_issued_items(db: DbSession, admin: User, ids: list[UUID]) -> int:
    items = db.scalars(
        select(PreRegistration)
        .where(PreRegistration.id.in_(ids), PreRegistration.tenant_id == admin.tenant_id)
        .with_for_update()
    ).all()
    if len(items) != len(set(ids)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "pre_registration_not_found"})
    if any(item.status != "issued" for item in items):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"code": "activated_pre_registration_cannot_be_deleted"})
    for item in items:
        db.delete(item)
    db.commit()
    return len(items)


@router.get("", response_model=PreRegistrationListResponse, summary="List imported accounts / 查询预注册账户")
def list_pre_registrations(
    db: DbSession,
    admin: User = Depends(require_roles("admin")),
    role: Literal["student", "mentor"] | None = Query(default=None),
    account_status: Literal["issued", "activated", "revoked"] | None = Query(default=None),
    search: str = Query(default="", max_length=100),
) -> PreRegistrationListResponse:
    statement = select(PreRegistration).where(PreRegistration.tenant_id == admin.tenant_id)
    if role is not None:
        statement = statement.where(PreRegistration.role_code == role)
    if account_status is not None:
        statement = statement.where(PreRegistration.status == account_status)
    if search.strip():
        pattern = f"%{search.strip()}%"
        statement = statement.where(or_(PreRegistration.username.ilike(pattern), PreRegistration.full_name.ilike(pattern), PreRegistration.academic_id.ilike(pattern), PreRegistration.institution_name_zh.ilike(pattern), PreRegistration.college_name_zh.ilike(pattern)))
    items = db.scalars(statement.order_by(PreRegistration.created_at.desc())).all()
    return PreRegistrationListResponse(items=[_pre_registration_response(item) for item in items], total=len(items))


@router.delete("/{pre_registration_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete an unactivated imported account / 删除未激活预注册账户")
def delete_pre_registration(
    pre_registration_id: UUID,
    db: DbSession,
    admin: User = Depends(require_roles("admin")),
) -> None:
    _delete_issued_items(db, admin, [pre_registration_id])


@router.post("/bulk-delete", status_code=status.HTTP_204_NO_CONTENT, summary="Batch delete unactivated imported accounts / 批量删除未激活预注册账户")
def bulk_delete_pre_registrations(
    payload: PreRegistrationBulkDeleteRequest,
    db: DbSession,
    admin: User = Depends(require_roles("admin")),
) -> None:
    _delete_issued_items(db, admin, payload.ids)


@router.get("/template", summary="Download pre-registration template / 下载预注册模板")
def download_template(_admin: User = Depends(require_roles("admin"))) -> Response:
    return Response(
        content=build_import_template(),
        media_type=XLSX_MEDIA_TYPE,
        headers={"Content-Disposition": 'attachment; filename="academicnexus-pre-registration-template.xlsx"'},
    )


@router.post("/import", status_code=status.HTTP_201_CREATED, summary="Import partner-school accounts / 导入合作院校账户")
async def import_workbook(
    file: Annotated[UploadFile, File(description="Partner-school pre-registration workbook / 合作院校预注册 Excel")],
    db: DbSession,
    _admin: User = Depends(require_roles("admin")),
) -> Response:
    filename = file.filename or "pre-registration.xlsx"
    if not filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=415, detail="Only .xlsx files are supported / 仅支持 .xlsx 文件")
    content = await file.read(MAX_IMPORT_SIZE + 1)
    if len(content) > MAX_IMPORT_SIZE:
        raise HTTPException(status_code=413, detail="Workbook exceeds 10 MB / Excel 文件超过 10 MB")
    try:
        batch, receipt_rows = import_pre_registrations(
            db,
            tenant_id=_admin.tenant_id,
            admin_user_id=_admin.id,
            source_filename=filename,
            content=content,
        )
    except PreRegistrationImportError as error:
        db.rollback()
        raise HTTPException(status_code=422, detail=error.errors) from error

    receipt = build_receipt_workbook(receipt_rows, batch.id)
    return Response(
        content=receipt,
        media_type=XLSX_MEDIA_TYPE,
        headers={
            "Content-Disposition": f'attachment; filename="academicnexus-account-receipt-{batch.id}.xlsx"',
            "X-Pre-Registration-Batch-Id": str(batch.id),
            "X-Pre-Registration-Count": str(batch.row_count),
        },
    )
