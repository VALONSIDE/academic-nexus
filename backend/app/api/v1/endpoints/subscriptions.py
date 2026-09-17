"""Subscription entitlement, institution inventory, and premium key APIs."""

from datetime import datetime, timezone
from io import BytesIO
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from fastapi.responses import StreamingResponse

from app.api.deps import DbSession, require_administrator, require_roles, require_super_admin
from app.models.subscription import InstitutionSubscriptionAllocation, PremiumSubscriptionKey
from app.models.user import User
from app.schemas.subscriptions import (
    InstitutionAdminAssignRequest,
    InstitutionAdminScopeResponse,
    InstitutionAccountResponse,
    InstitutionAllocationRequest,
    InstitutionAllocationResponse,
    InstitutionOptionResponse,
    PremiumSubscriptionKeyBatchIssueRequest,
    PremiumSubscriptionKeyResponse,
    SubscriptionKeyDeliveryActivationResponse,
    SubscriptionKeyDeliveryBatchRequest,
    SubscriptionKeyDeliveryValidationResponse,
    SubscriptionKeyActivateRequest,
    SubscriptionResponse,
)
from app.services.subscriptions import (
    SubscriptionError,
    active_premium_subscription_user_ids,
    activate_subscription_key,
    assign_institution_admin,
    build_subscription_key_receipt,
    issue_subscription_keys,
    list_allocations,
    list_institution_accounts,
    list_institution_admin_scopes,
    list_institutions,
    list_my_institution_admin_scopes,
    list_subscription_keys,
    revoke_institution_admin,
    revoke_subscription_key,
    set_institution_allocation,
    subscription_snapshot,
)
from app.services.subscription_delivery import (
    DeliveryItem,
    activate_subscription_delivery_items,
    build_subscription_delivery_pdf_bundle,
    extract_subscription_keys_from_workbook,
    validate_imported_subscription_keys,
)

router = APIRouter(prefix="/subscriptions", tags=["Subscriptions / 订阅"])
admin_router = APIRouter(prefix="/admin/subscriptions", tags=["Subscription administration / 订阅管理"])

delivery_router = APIRouter(prefix="/admin/subscription-delivery", tags=["Offline subscription delivery"])


def _subscription_response(snapshot) -> SubscriptionResponse:
    return SubscriptionResponse(
        plan_code=snapshot.plan_code,
        credit_limit=snapshot.credit_limit,
        credit_balance=snapshot.credit_balance,
        credits_used=snapshot.credits_used,
        cycle_started_at=snapshot.cycle_started_at,
        cycle_ends_at=snapshot.cycle_ends_at,
    )


def _allocation_response(allocation: InstitutionSubscriptionAllocation) -> InstitutionAllocationResponse:
    return InstitutionAllocationResponse(
        institution_abbr=allocation.institution_abbr,
        institution_name_zh=allocation.institution_name_zh,
        pro_credits=allocation.pro_credits,
        ultra_credits=allocation.ultra_credits,
        max_credits=allocation.max_credits,
    )


def _key_response(key: PremiumSubscriptionKey) -> PremiumSubscriptionKeyResponse:
    return PremiumSubscriptionKeyResponse(
        id=key.id,
        institution_abbr=key.institution_abbr,
        institution_name_zh=key.institution_name_zh,
        plan_code=key.plan_code,
        status=key.status,
        issued_at=key.issued_at,
        activated_at=key.activated_at,
        revoked_at=key.revoked_at,
    )


def _scope_response(scope, user: User | None = None) -> InstitutionAdminScopeResponse:
    return InstitutionAdminScopeResponse(
        id=scope.id,
        user_id=scope.user_id,
        username=(user.username if user and user.username else ""),
        full_name=user.full_name if user else "",
        institution_abbr=scope.institution_abbr,
        institution_name_zh=scope.institution_name_zh,
        created_at=scope.created_at,
    )


def _raise_subscription_error(error: SubscriptionError) -> None:
    status_code = status.HTTP_400_BAD_REQUEST
    if error.code in {"institution_scope_forbidden", "super_admin_required"}:
        status_code = status.HTTP_403_FORBIDDEN
    elif error.code in {"institution_allocation_not_found", "institution_not_found", "institution_admin_scope_not_found", "subscription_key_not_found"}:
        status_code = status.HTTP_404_NOT_FOUND
    elif error.code in {
        "institution_admin_user_ineligible",
        "subscription_delivery_workbook_invalid",
        "subscription_delivery_workbook_no_keys",
        "subscription_delivery_item_limit",
        "subscription_delivery_items_invalid",
        "subscription_delivery_recipient_ineligible",
        "subscription_delivery_recipient_required",
    }:
        status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    elif error.code in {
        "active_premium_plan_locked",
        "subscription_key_not_reclaimable",
        "subscription_delivery_key_unavailable",
        "subscription_delivery_recipient_already_subscribed",
    }:
        status_code = status.HTTP_409_CONFLICT
    elif error.code == "subscription_inventory_exhausted":
        status_code = status.HTTP_409_CONFLICT
    raise HTTPException(status_code=status_code, detail={"code": error.code}) from error


@router.get("/me", response_model=SubscriptionResponse, summary="Read current subscription / 获取当前订阅")
def read_my_subscription(
    db: DbSession,
    current_user: User = Depends(require_roles("student", "mentor")),
) -> SubscriptionResponse:
    response = _subscription_response(subscription_snapshot(db, current_user))
    db.commit()
    return response


@router.post("/activate", response_model=SubscriptionResponse, summary="Redeem premium key / 兑换高级订阅 Key")
def activate_my_subscription(
    payload: SubscriptionKeyActivateRequest,
    db: DbSession,
    current_user: User = Depends(require_roles("student", "mentor")),
) -> SubscriptionResponse:
    try:
        return _subscription_response(activate_subscription_key(db, current_user, raw_key=payload.key))
    except SubscriptionError as error:
        _raise_subscription_error(error)


@admin_router.get("/allocations", response_model=list[InstitutionAllocationResponse], summary="List institution inventory / 查询院校高级订阅额度")
def read_allocations(
    db: DbSession,
    admin: User = Depends(require_administrator),
) -> list[InstitutionAllocationResponse]:
    return [_allocation_response(item) for item in list_allocations(db, admin)]


@admin_router.put("/allocations/{institution_abbr}", response_model=InstitutionAllocationResponse, summary="Set institution inventory / 分配院校高级订阅额度")
def save_allocation(
    institution_abbr: str,
    payload: InstitutionAllocationRequest,
    db: DbSession,
    super_admin: User = Depends(require_super_admin),
) -> InstitutionAllocationResponse:
    try:
        allocation = set_institution_allocation(
            db,
            super_admin,
            institution_abbr=institution_abbr.strip().upper(),
            pro_credits=payload.pro_credits,
            ultra_credits=payload.ultra_credits,
            max_credits=payload.max_credits,
        )
        return _allocation_response(allocation)
    except SubscriptionError as error:
        _raise_subscription_error(error)


@admin_router.get("/institution-admins", response_model=list[InstitutionAdminScopeResponse], summary="List institution administrators / 查询院校管理员")
def read_institution_administrators(
    db: DbSession,
    super_admin: User = Depends(require_super_admin),
) -> list[InstitutionAdminScopeResponse]:
    return [
        _scope_response(scope, user)
        for scope, user in list_institution_admin_scopes(db, super_admin)
    ]


@admin_router.get("/institutions", response_model=list[InstitutionOptionResponse], summary="List trusted institutions")
def read_institutions(
    db: DbSession,
    super_admin: User = Depends(require_super_admin),
) -> list[InstitutionOptionResponse]:
    return [InstitutionOptionResponse(**item.__dict__) for item in list_institutions(db, super_admin)]


@admin_router.get("/institutions/{institution_abbr}/accounts", response_model=list[InstitutionAccountResponse], summary="List selectable institution accounts")
def read_institution_accounts(
    institution_abbr: str,
    db: DbSession,
    admin: User = Depends(require_administrator),
) -> list[InstitutionAccountResponse]:
    accounts = list_institution_accounts(db, admin, institution_abbr)
    active_premium_ids = active_premium_subscription_user_ids(db, [account.id for account in accounts])
    response: list[InstitutionAccountResponse] = []
    for account in accounts:
        role = "student" if any(item.code == "student" for item in account.roles) else "mentor"
        response.append(
            InstitutionAccountResponse(
                id=account.id,
                username=account.username or "",
                full_name=account.full_name,
                role=role,
                has_active_premium_subscription=account.id in active_premium_ids,
            )
        )
    return response


@admin_router.get("/my-scopes", response_model=list[InstitutionAdminScopeResponse], summary="Read current institution-admin scopes")
def read_my_institution_administrator_scopes(
    db: DbSession,
    admin: User = Depends(require_administrator),
) -> list[InstitutionAdminScopeResponse]:
    return [_scope_response(scope) for scope in list_my_institution_admin_scopes(db, admin)]


@admin_router.post("/institution-admins", response_model=InstitutionAdminScopeResponse, status_code=status.HTTP_201_CREATED, summary="Assign institution administrator / 指派院校管理员")
def create_institution_administrator(
    payload: InstitutionAdminAssignRequest,
    db: DbSession,
    super_admin: User = Depends(require_super_admin),
) -> InstitutionAdminScopeResponse:
    try:
        scope = assign_institution_admin(
            db,
            super_admin,
            user_id=payload.user_id,
            institution_abbr=payload.institution_abbr,
        )
        # The assignment service has already resolved the target account.
        from sqlalchemy import select
        target = db.scalar(select(User).where(User.id == scope.user_id))
        return _scope_response(scope, target)
    except SubscriptionError as error:
        _raise_subscription_error(error)


@admin_router.delete("/institution-admins/{scope_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Remove institution administrator assignment")
def delete_institution_administrator(
    scope_id: UUID,
    db: DbSession,
    super_admin: User = Depends(require_super_admin),
) -> None:
    try:
        revoke_institution_admin(db, super_admin, scope_id)
    except SubscriptionError as error:
        _raise_subscription_error(error)


@admin_router.get("/keys", response_model=list[PremiumSubscriptionKeyResponse], summary="List premium keys / 查询高级订阅 Key")
def read_subscription_keys(
    db: DbSession,
    admin: User = Depends(require_administrator),
) -> list[PremiumSubscriptionKeyResponse]:
    return [_key_response(item) for item in list_subscription_keys(db, admin)]


@admin_router.post("/keys/batch", status_code=status.HTTP_201_CREATED, summary="Issue premium keys and export receipt")
def create_subscription_key_batch(
    payload: PremiumSubscriptionKeyBatchIssueRequest,
    db: DbSession,
    admin: User = Depends(require_administrator),
) -> StreamingResponse:
    try:
        issued = issue_subscription_keys(
            db,
            admin,
            institution_abbr=payload.institution_abbr,
            plan_code=payload.plan_code,
            quantity=payload.quantity,
        )
        filename = f"academicnexus-subscription-keys-{payload.institution_abbr}-{payload.plan_code}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.xlsx"
        return StreamingResponse(
            BytesIO(build_subscription_key_receipt(issued)),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "X-Subscription-Key-Count": str(len(issued)),
                "Cache-Control": "no-store, private",
                "Pragma": "no-cache",
            },
        )
    except SubscriptionError as error:
        _raise_subscription_error(error)


@admin_router.delete("/keys/{key_id}", response_model=PremiumSubscriptionKeyResponse, summary="Reclaim unused premium key / 收回未激活高级订阅 Key")
def delete_subscription_key(
    key_id: UUID,
    db: DbSession,
    admin: User = Depends(require_administrator),
) -> PremiumSubscriptionKeyResponse:
    try:
        return _key_response(revoke_subscription_key(db, admin, key_id))
    except SubscriptionError as error:
        _raise_subscription_error(error)


@delivery_router.post("/validate-excel", response_model=list[SubscriptionKeyDeliveryValidationResponse], summary="Validate an offline subscription-key receipt")
def validate_subscription_delivery_workbook(
    db: DbSession,
    response: Response,
    file: UploadFile = File(...),
    admin: User = Depends(require_administrator),
) -> list[SubscriptionKeyDeliveryValidationResponse]:
    if not file.filename or not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail={"code": "subscription_delivery_workbook_invalid"})
    # The receipt and its keys live only in bounded request memory.  Nothing is
    # written to disk or persisted while the receipt is being checked.
    try:
        content = file.file.read(512 * 1024 + 1)
    finally:
        file.file.close()
    try:
        imported = extract_subscription_keys_from_workbook(content)
        response.headers["Cache-Control"] = "no-store, private"
        response.headers["Pragma"] = "no-cache"
        return [
            SubscriptionKeyDeliveryValidationResponse(
                row_number=item.row_number,
                key=item.raw_key,
                plan_code=item.plan_code,
                institution_abbr=item.institution_abbr,
                institution_name_zh=item.institution_name_zh,
                status=item.status,
            )
            for item in validate_imported_subscription_keys(db, admin, imported)
        ]
    except SubscriptionError as error:
        _raise_subscription_error(error)


@delivery_router.post("/activate", response_model=SubscriptionKeyDeliveryActivationResponse, summary="Directly activate selected users from an offline key receipt")
def directly_activate_subscription_delivery(
    payload: SubscriptionKeyDeliveryBatchRequest,
    db: DbSession,
    admin: User = Depends(require_administrator),
) -> SubscriptionKeyDeliveryActivationResponse:
    try:
        activate_subscription_delivery_items(db, admin, [DeliveryItem(raw_key=item.key, recipient_user_id=item.recipient_user_id) for item in payload.items])
        return SubscriptionKeyDeliveryActivationResponse(activated_count=len(payload.items))
    except SubscriptionError as error:
        db.rollback()
        _raise_subscription_error(error)


@delivery_router.post("/export-pdf", summary="Export selected offline subscription notices as a ZIP")
def export_subscription_delivery_pdfs(
    payload: SubscriptionKeyDeliveryBatchRequest,
    db: DbSession,
    admin: User = Depends(require_administrator),
) -> StreamingResponse:
    try:
        bundle = build_subscription_delivery_pdf_bundle(db, admin, [DeliveryItem(raw_key=item.key, recipient_user_id=item.recipient_user_id) for item in payload.items])
        # Export does not consume a Key or otherwise mutate state.  Release
        # verification locks before streaming the in-memory archive.
        db.rollback()
        filename = f"academicnexus-subscription-notices-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.zip"
        return StreamingResponse(
            BytesIO(bundle),
            media_type="application/zip",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Cache-Control": "no-store, private",
                "Pragma": "no-cache",
            },
        )
    except SubscriptionError as error:
        db.rollback()
        _raise_subscription_error(error)
