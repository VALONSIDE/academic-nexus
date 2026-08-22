from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.orm import selectinload

from app.api.deps import DbSession, require_roles
from app.models.ai import AiConversation, AiMessage
from app.models.user import User
from app.schemas.ai import (
    AdminAiQuotaListResponse,
    AdminAiQuotaUpdateRequest,
    AdminAiQuotaUserResponse,
    AiChatResponse,
    AiConversationCreateRequest,
    AiConversationDetailResponse,
    AiConversationResponse,
    AiMessageCreateRequest,
    AiMessageResponse,
    AiQuotaResponse,
)
from app.services.ai.assistant import AiAssistantError, create_conversation, get_conversation, list_conversations, list_messages, send_message
from app.services.ai.quota import AiQuotaExceededError, QuotaSnapshot, quota_snapshot, update_user_quota

router = APIRouter(prefix="/ai", tags=["AI assistant / AI 助手"])
admin_router = APIRouter(prefix="/admin/ai", tags=["AI administration / AI 管理"])
ManagedRole = Literal["student", "mentor"]


def _quota_response(snapshot: QuotaSnapshot) -> AiQuotaResponse:
    return AiQuotaResponse(
        plan_code=snapshot.plan_code,
        daily_limit=snapshot.daily_limit,
        daily_used=snapshot.daily_used,
        daily_remaining=snapshot.daily_remaining,
        credit_balance=snapshot.credit_balance,
        project_daily_limit=snapshot.project_daily_limit,
        project_daily_used=snapshot.project_daily_used,
        project_daily_remaining=snapshot.project_daily_remaining,
    )


def _message_response(message: AiMessage) -> AiMessageResponse:
    return AiMessageResponse(id=message.id, role=message.role, content=message.content, created_at=message.created_at)


def _conversation_response(conversation: AiConversation) -> AiConversationResponse:
    return AiConversationResponse(
        id=conversation.id,
        topic=conversation.topic,
        title=conversation.title,
        last_message_at=conversation.last_message_at,
        created_at=conversation.created_at,
    )


def _raise_assistant_error(error: AiAssistantError | AiQuotaExceededError) -> None:
    if isinstance(error, AiQuotaExceededError):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"code": error.code},
        ) from error
    if error.code == "provider_not_configured":
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail={"code": error.code}) from error
    raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail={"code": error.code}) from error


@router.get("/quota", response_model=AiQuotaResponse, summary="Read personal AI quota / 获取个人 AI 配额")
def read_personal_quota(db: DbSession, current_user: User = Depends(require_roles("student", "mentor"))) -> AiQuotaResponse:
    snapshot = quota_snapshot(db, current_user.id)
    db.commit()
    return _quota_response(snapshot)


@router.get("/conversations", response_model=list[AiConversationResponse], summary="List AI conversations / 查询 AI 会话")
def read_conversations(db: DbSession, current_user: User = Depends(require_roles("student", "mentor"))) -> list[AiConversationResponse]:
    return [_conversation_response(item) for item in list_conversations(db, current_user)]


@router.post("/conversations", response_model=AiConversationResponse, status_code=status.HTTP_201_CREATED, summary="Create AI conversation / 创建 AI 会话")
def create_ai_conversation(
    payload: AiConversationCreateRequest,
    db: DbSession,
    current_user: User = Depends(require_roles("student", "mentor")),
) -> AiConversationResponse:
    return _conversation_response(create_conversation(db, current_user, topic=payload.topic, title=payload.title))


@router.get("/conversations/{conversation_id}", response_model=AiConversationDetailResponse, summary="Read AI conversation / 获取 AI 会话")
def read_conversation(
    conversation_id: UUID,
    db: DbSession,
    current_user: User = Depends(require_roles("student", "mentor")),
) -> AiConversationDetailResponse:
    conversation = get_conversation(db, current_user, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found / 未找到会话")
    base = _conversation_response(conversation)
    return AiConversationDetailResponse(**base.model_dump(), messages=[_message_response(item) for item in list_messages(db, conversation)])


@router.post("/conversations/{conversation_id}/messages", response_model=AiChatResponse, summary="Send AI chat message / 发送 AI 对话消息")
def send_ai_message(
    conversation_id: UUID,
    payload: AiMessageCreateRequest,
    db: DbSession,
    current_user: User = Depends(require_roles("student", "mentor")),
) -> AiChatResponse:
    conversation = get_conversation(db, current_user, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found / 未找到会话")
    try:
        user_message, assistant_message = send_message(db, current_user, conversation, content=payload.content)
    except (AiAssistantError, AiQuotaExceededError) as error:
        _raise_assistant_error(error)
    snapshot = quota_snapshot(db, current_user.id)
    db.commit()
    return AiChatResponse(
        user_message=_message_response(user_message),
        assistant_message=_message_response(assistant_message),
        quota=_quota_response(snapshot),
    )


def _managed_role(user: User) -> ManagedRole | None:
    if any(role.code == "student" for role in user.roles):
        return "student"
    if any(role.code == "mentor" for role in user.roles):
        return "mentor"
    return None


@admin_router.get("/quotas", response_model=AdminAiQuotaListResponse, summary="List AI quotas / 查询 AI 配额")
def list_ai_quotas(
    db: DbSession,
    admin: User = Depends(require_roles("admin")),
    role: ManagedRole | None = Query(default=None),
    search: str = Query(default="", max_length=100),
) -> AdminAiQuotaListResponse:
    statement = (
        select(User)
        .options(selectinload(User.roles))
        .where(User.tenant_id == admin.tenant_id)
        .where(User.roles.any(code="student") | User.roles.any(code="mentor"))
        .order_by(User.created_at.desc())
    )
    if role is not None:
        statement = statement.where(User.roles.any(code=role))
    if search.strip():
        pattern = f"%{search.strip()}%"
        statement = statement.where(or_(User.username.ilike(pattern), User.full_name.ilike(pattern)))
    users = db.scalars(statement).unique().all()
    items: list[AdminAiQuotaUserResponse] = []
    project_snapshot: QuotaSnapshot | None = None
    for user in users:
        user_role = _managed_role(user)
        if user_role is None:
            continue
        snapshot = quota_snapshot(db, user.id)
        project_snapshot = snapshot
        items.append(
            AdminAiQuotaUserResponse(
                user_id=user.id,
                username=user.username or "",
                full_name=user.full_name,
                role=user_role,
                plan_code=snapshot.plan_code,
                daily_limit=snapshot.daily_limit,
                daily_used=snapshot.daily_used,
                credit_balance=snapshot.credit_balance,
            )
        )
    if project_snapshot is None:
        # Read a project snapshot through the administrator without exposing their quota in the list.
        project_snapshot = quota_snapshot(db, admin.id)
    db.commit()
    return AdminAiQuotaListResponse(
        items=items,
        total=len(items),
        project_daily_limit=project_snapshot.project_daily_limit,
        project_daily_used=project_snapshot.project_daily_used,
        project_daily_remaining=project_snapshot.project_daily_remaining,
    )


@admin_router.patch("/quotas/{user_id}", response_model=AiQuotaResponse, summary="Update AI quota / 更新 AI 配额")
def update_ai_quota(
    user_id: UUID,
    payload: AdminAiQuotaUpdateRequest,
    db: DbSession,
    admin: User = Depends(require_roles("admin")),
) -> AiQuotaResponse:
    target = db.scalar(select(User).options(selectinload(User.roles)).where(User.id == user_id, User.tenant_id == admin.tenant_id))
    if target is None or _managed_role(target) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found / 未找到用户")
    try:
        snapshot = update_user_quota(
            db,
            user_id=target.id,
            daily_limit=payload.daily_limit,
            credit_balance=payload.credit_balance,
            daily_used=payload.daily_used,
            plan_code=payload.plan_code,
        )
    except AiQuotaExceededError as error:
        _raise_assistant_error(error)
    return _quota_response(snapshot)
