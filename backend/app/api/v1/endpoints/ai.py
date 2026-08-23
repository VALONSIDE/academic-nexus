import json
from collections.abc import Iterator
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import or_, select
from sqlalchemy.orm import selectinload

from app.api.deps import DbSession, require_roles, require_super_admin
from app.models.ai import AiConversation, AiMessage
from app.models.user import User
from app.schemas.ai import (
    AdminAiQuotaListResponse,
    AdminAiQuotaUpdateRequest,
    AdminAiQuotaUserResponse,
    AiChatResponse,
    AiConversationCreateRequest,
    AiConversationDetailResponse,
    AiConversationRenameRequest,
    AiConversationResponse,
    AiMessageCreateRequest,
    AiMessageResponse,
    AiQuotaResponse,
)
from app.services.ai.assistant import AiAssistantError, create_conversation, delete_conversation, get_conversation, list_conversations, list_messages, rename_conversation, send_message, stream_message
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
        cycle_started_at=snapshot.cycle_started_at,
        cycle_ends_at=snapshot.cycle_ends_at,
        cycle_credit_limit=snapshot.cycle_credit_limit,
        cycle_credits_used=snapshot.cycle_credits_used,
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


def _sse(event: str, payload: object) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


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


@router.patch("/conversations/{conversation_id}", response_model=AiConversationResponse, summary="Rename AI conversation / 修改 AI 会话名称")
def rename_ai_conversation(
    conversation_id: UUID,
    payload: AiConversationRenameRequest,
    db: DbSession,
    current_user: User = Depends(require_roles("student", "mentor")),
) -> AiConversationResponse:
    conversation = get_conversation(db, current_user, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found / 未找到会话")
    return _conversation_response(rename_conversation(db, conversation, title=payload.title))


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete AI conversation / 删除 AI 对话")
def delete_ai_conversation(
    conversation_id: UUID,
    db: DbSession,
    current_user: User = Depends(require_roles("student", "mentor")),
) -> None:
    conversation = get_conversation(db, current_user, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found / 未找到会话")
    delete_conversation(db, conversation)


@router.post("/conversations/{conversation_id}/messages", response_model=AiChatResponse, summary="Send AI chat message / 发送 AI 对话消息")
def send_ai_message(
    conversation_id: UUID,
    payload: AiMessageCreateRequest,
    db: DbSession,
    current_user: User = Depends(require_roles("student", "mentor")),
) -> AiChatResponse | StreamingResponse:
    conversation = get_conversation(db, current_user, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found / 未找到会话")
    if payload.response_mode == "stream":
        def event_stream() -> Iterator[str]:
            try:
                for event in stream_message(
                    db,
                    current_user,
                    conversation,
                    content=payload.content,
                    model_tier=payload.model_tier,
                ):
                    if event.text:
                        yield _sse("text", {"text": event.text})
                    elif event.user_message is not None and event.assistant_message is not None:
                        snapshot = quota_snapshot(db, current_user.id)
                        db.commit()
                        result = AiChatResponse(
                            user_message=_message_response(event.user_message),
                            assistant_message=_message_response(event.assistant_message),
                            quota=_quota_response(snapshot),
                        )
                        yield _sse("done", result.model_dump(mode="json"))
            except (AiAssistantError, AiQuotaExceededError) as error:
                yield _sse("error", {"code": error.code})

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    try:
        user_message, assistant_message = send_message(
            db,
            current_user,
            conversation,
            content=payload.content,
            model_tier=payload.model_tier,
        )
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
    admin: User = Depends(require_super_admin),
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
    admin: User = Depends(require_super_admin),
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
