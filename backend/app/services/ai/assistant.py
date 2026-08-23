"""Conversation persistence and bounded-context orchestration for AcademicNexus AI."""

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.ai import AiConversation, AiMessage
from app.models.user import User
from app.services.matching import mentor_recommendations, student_candidates
from app.services.ai.minimax import MiniMaxConfigurationError, MiniMaxRequestError, request_completion, stream_completion
from app.services.ai.quota import complete_ai_call, release_ai_call, reserve_ai_call


class AiAssistantError(RuntimeError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


DEFAULT_CONVERSATION_TITLE = "New conversation"
MAX_CONVERSATIONS_PER_USER = 100


@dataclass(frozen=True)
class AiModelProfile:
    model: str
    credit_cost: int


@dataclass(frozen=True)
class AiStreamEvent:
    text: str = ""
    user_message: AiMessage | None = None
    assistant_message: AiMessage | None = None


def model_profile(tier: str) -> AiModelProfile:
    settings = get_settings()
    profiles = {
        "light": AiModelProfile(model=settings.minimax_light_model, credit_cost=1),
        "standard": AiModelProfile(model=settings.minimax_standard_model, credit_cost=1),
        "expert": AiModelProfile(model=settings.minimax_expert_model, credit_cost=2),
    }
    try:
        return profiles[tier]
    except KeyError as error:
        raise AiAssistantError("invalid_model_tier") from error


TOPIC_GUIDANCE = {
    "academic_planning": {
        "zh-CN": "帮助用户梳理学术目标、阶段计划、风险和可执行的下一步。",
        "en-US": "Help the user clarify academic goals, milestones, risks, and concrete next steps.",
    },
    "mentor_consultation": {
        "zh-CN": "帮助用户准备导师沟通、理解研究契合点，并给出礼貌且可执行的建议。",
        "en-US": "Help the user prepare mentor communication, understand research fit, and give practical respectful advice.",
    },
    "learning_roadmap": {
        "zh-CN": "帮助用户生成包含前置关系、时间估计和复盘节点的学习路线。",
        "en-US": "Help the user create a learning roadmap with prerequisites, time estimates, and review checkpoints.",
    },
    "selection_advisor": {
        "zh-CN": "基于同校候选池、学院归属与双方公开学术画像，解释匹配优先级并帮助用户比较候选人。",
        "en-US": "Use the same-institution candidate pool, college affiliation, and public academic portraits to explain match priority and compare candidates.",
    },
}


def create_conversation(db: Session, user: User, *, topic: str, title: str | None = None) -> AiConversation:
    # Serialize creation per account.  A server-side cap prevents a user from
    # bypassing the UI's history handling by opening multiple tabs or calling the
    # API directly.
    db.execute(select(User.id).where(User.id == user.id).with_for_update())
    conversation = AiConversation(
        tenant_id=user.tenant_id,
        user_id=user.id,
        topic=topic,
        title=title or DEFAULT_CONVERSATION_TITLE,
        created_at=datetime.now(timezone.utc),
    )
    db.add(conversation)
    db.flush()
    history = list(
        db.scalars(
            select(AiConversation)
            .where(AiConversation.user_id == user.id, AiConversation.tenant_id == user.tenant_id)
            .order_by(AiConversation.created_at.asc(), AiConversation.id.asc())
        ).all()
    )
    for item in history[:-MAX_CONVERSATIONS_PER_USER]:
        db.delete(item)
    db.commit()
    db.refresh(conversation)
    return conversation


def list_conversations(db: Session, user: User) -> list[AiConversation]:
    return list(db.scalars(select(AiConversation).where(AiConversation.user_id == user.id, AiConversation.tenant_id == user.tenant_id, AiConversation.is_archived.is_(False)).order_by(AiConversation.last_message_at.desc().nullslast(), AiConversation.created_at.desc())).all())


def get_conversation(db: Session, user: User, conversation_id) -> AiConversation | None:
    return db.scalar(select(AiConversation).where(AiConversation.id == conversation_id, AiConversation.user_id == user.id, AiConversation.tenant_id == user.tenant_id))


def rename_conversation(db: Session, conversation: AiConversation, *, title: str) -> AiConversation:
    conversation.title = title
    db.commit()
    db.refresh(conversation)
    return conversation


def delete_conversation(db: Session, conversation: AiConversation) -> None:
    """Permanently delete one owned conversation and its message history."""
    db.delete(conversation)
    db.commit()


def list_messages(db: Session, conversation: AiConversation) -> list[AiMessage]:
    return list(db.scalars(select(AiMessage).where(AiMessage.conversation_id == conversation.id).order_by(AiMessage.created_at.asc())).all())


def _profile_context(user: User) -> str:
    if user.student_profile is not None:
        profile = user.student_profile
        return f"Role: student\nInstitution: {profile.university or ''}\nCollege: {profile.department or ''}\nResearch interests: {', '.join(profile.research_interests or [])}\nSkills: {', '.join(profile.skills or [])}\nAcademic goals: {profile.academic_goals or ''}\nResearch experience: {profile.research_experience or ''}"
    if user.mentor_profile is not None:
        profile = user.mentor_profile
        return f"Role: mentor\nInstitution: {profile.university or ''}\nCollege: {profile.department or ''}\nResearch directions: {', '.join(profile.research_directions or [])}\nRepresentative papers: {', '.join(profile.representative_papers or [])}\nProjects: {profile.research_projects or ''}\nMentoring style: {profile.mentoring_style or ''}"
    return "Role: platform user"


def _selection_advisor_context(db: Session, user: User) -> str:
    """Expose only the candidate portraits that the user can already view in mutual selection."""
    if user.student_profile is not None:
        matches = mentor_recommendations(db, user, limit=25)
        entries = [
            " | ".join(
                filter(
                    None,
                    [
                        f"Mentor: {mentor.full_name}",
                        f"Institution: {mentor.mentor_profile.university}",
                        f"College: {mentor.mentor_profile.department}",
                        f"Title: {mentor.mentor_profile.title}",
                        f"Research: {', '.join(mentor.mentor_profile.research_directions or [])}",
                        f"Style: {mentor.mentor_profile.mentoring_style}",
                        f"Match score: {score.score}",
                    ],
                )
            )
            for mentor, score in matches
        ]
        return "Visible same-institution mentor candidates:\n" + ("\n".join(entries) if entries else "No candidates available yet.")
    if user.mentor_profile is not None:
        matches = student_candidates(db, user, limit=25)
        entries = [
            " | ".join(
                filter(
                    None,
                    [
                        f"Student: {student.full_name}",
                        f"Institution: {student.student_profile.university}",
                        f"College: {student.student_profile.department}",
                        f"Major: {student.student_profile.major}",
                        f"Interests: {', '.join(student.student_profile.research_interests or [])}",
                        f"Skills: {', '.join(student.student_profile.skills or [])}",
                        f"Goals: {student.student_profile.academic_goals}",
                        f"Match score: {score.score}",
                    ],
                )
            )
            for student, score in matches
        ]
        return "Visible same-institution student candidates:\n" + ("\n".join(entries) if entries else "No candidates available yet.")
    return "No completed academic portrait is available."


def _system_prompt(db: Session, user: User, conversation: AiConversation) -> str:
    locale = user.preferred_locale if user.preferred_locale in {"zh-CN", "en-US"} else "zh-CN"
    guidance = TOPIC_GUIDANCE[conversation.topic][locale]
    context = _profile_context(user)
    selection_context = _selection_advisor_context(db, user) if conversation.topic == "selection_advisor" else ""
    if locale == "zh-CN":
        return (
            "你是 AcademicNexus（智导未来）的学术发展助手。回答应清晰、审慎、可执行。"
            "不要编造论文、导师或项目事实；涉及录取、心理或医疗等高风险事项时，应建议咨询合格专业人员。\n"
            f"当前专题：{guidance}\n用户画像（仅用于个性化建议）：\n{context}\n"
            f"{selection_context}\n"
            "画像信息不足时，先提出最少且必要的澄清问题。请使用中文回答。"
        )
    return (
        "You are AcademicNexus's academic-development assistant. Be clear, careful, and actionable. "
        "Do not invent facts about papers, mentors, or projects. For high-stakes admissions, mental-health, or medical matters, suggest qualified professional support.\n"
        f"Current focus: {guidance}\nUser portrait (only for personalized advice):\n{context}\n"
        f"{selection_context}\n"
        "Ask the minimum useful clarification when the portrait is insufficient. Reply in English."
    )


def _bounded_messages(db: Session, conversation: AiConversation) -> list[dict[str, object]]:
    settings = get_settings()
    newest = list(db.scalars(select(AiMessage).where(AiMessage.conversation_id == conversation.id).order_by(AiMessage.created_at.desc()).limit(settings.ai_context_message_limit)).all())
    remaining = settings.ai_context_character_limit
    payload: list[dict[str, object]] = []
    for message in reversed(newest):
        content = message.content[-remaining:] if len(message.content) > remaining else message.content
        remaining = max(0, remaining - len(content))
        if content:
            payload.append({"role": message.role, "content": [{"type": "text", "text": content}]})
    return payload


def _begin_turn(
    db: Session,
    user: User,
    conversation: AiConversation,
    *,
    content: str,
    profile: AiModelProfile,
):
    event = reserve_ai_call(db, user, conversation.id, model=profile.model, credit_cost=profile.credit_cost)
    original_title = conversation.title
    original_last_message_at = conversation.last_message_at
    user_message = AiMessage(conversation_id=conversation.id, role="user", content=content)
    db.add(user_message)
    if conversation.title == DEFAULT_CONVERSATION_TITLE:
        conversation.title = content[:80]
    conversation.last_message_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user_message)
    return event, user_message, original_title, original_last_message_at


def _revert_turn(
    db: Session,
    conversation: AiConversation,
    *,
    user_message: AiMessage,
    event_id,
    original_title: str,
    original_last_message_at: datetime | None,
    error_code: str,
) -> None:
    db.execute(delete(AiMessage).where(AiMessage.id == user_message.id))
    conversation.title = original_title
    conversation.last_message_at = original_last_message_at
    db.commit()
    release_ai_call(db, event_id, error_code=error_code)


def _persist_reply(
    db: Session,
    conversation: AiConversation,
    *,
    event_id,
    content: str,
    input_tokens: int | None,
    output_tokens: int | None,
) -> AiMessage:
    assistant_message = AiMessage(
        conversation_id=conversation.id,
        role="assistant",
        content=content,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )
    db.add(assistant_message)
    conversation.last_message_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(assistant_message)
    complete_ai_call(db, event_id, input_tokens=input_tokens, output_tokens=output_tokens)
    return assistant_message


def send_message(
    db: Session,
    user: User,
    conversation: AiConversation,
    *,
    content: str,
    model_tier: str = "standard",
) -> tuple[AiMessage, AiMessage]:
    """Reserve the selected model cost, persist a turn, invoke MiniMax, and refund failures."""
    profile = model_profile(model_tier)
    event, user_message, original_title, original_last_message_at = _begin_turn(
        db,
        user,
        conversation,
        content=content,
        profile=profile,
    )
    try:
        reply = request_completion(
            system=_system_prompt(db, user, conversation),
            messages=_bounded_messages(db, conversation),
            model=profile.model,
        )
    except MiniMaxConfigurationError as error:
        _revert_turn(db, conversation, user_message=user_message, event_id=event.id, original_title=original_title, original_last_message_at=original_last_message_at, error_code="provider_not_configured")
        raise AiAssistantError("provider_not_configured") from error
    except MiniMaxRequestError as error:
        _revert_turn(db, conversation, user_message=user_message, event_id=event.id, original_title=original_title, original_last_message_at=original_last_message_at, error_code="provider_request_failed")
        raise AiAssistantError("provider_request_failed") from error
    assistant_message = _persist_reply(db, conversation, event_id=event.id, content=reply.content, input_tokens=reply.input_tokens, output_tokens=reply.output_tokens)
    return user_message, assistant_message


def stream_message(
    db: Session,
    user: User,
    conversation: AiConversation,
    *,
    content: str,
    model_tier: str = "standard",
) -> Iterator[AiStreamEvent]:
    """Persist a streaming MiniMax turn while emitting only answer text deltas."""
    profile = model_profile(model_tier)
    event, user_message, original_title, original_last_message_at = _begin_turn(
        db,
        user,
        conversation,
        content=content,
        profile=profile,
    )
    pieces: list[str] = []
    try:
        for provider_event in stream_completion(
            system=_system_prompt(db, user, conversation),
            messages=_bounded_messages(db, conversation),
            model=profile.model,
        ):
            if provider_event.text:
                pieces.append(provider_event.text)
                yield AiStreamEvent(text=provider_event.text)
            if provider_event.completed:
                assistant_message = _persist_reply(
                    db,
                    conversation,
                    event_id=event.id,
                    content="".join(pieces).strip(),
                    input_tokens=provider_event.input_tokens,
                    output_tokens=provider_event.output_tokens,
                )
                yield AiStreamEvent(user_message=user_message, assistant_message=assistant_message)
    except MiniMaxConfigurationError as error:
        _revert_turn(db, conversation, user_message=user_message, event_id=event.id, original_title=original_title, original_last_message_at=original_last_message_at, error_code="provider_not_configured")
        raise AiAssistantError("provider_not_configured") from error
    except MiniMaxRequestError as error:
        _revert_turn(db, conversation, user_message=user_message, event_id=event.id, original_title=original_title, original_last_message_at=original_last_message_at, error_code="provider_request_failed")
        raise AiAssistantError("provider_request_failed") from error
