from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import and_, select

from app.models.ai import AiMessage
from app.models.selection import MentorSelection
from app.models.user import MentorProfile, StudentProfile, User
from app.services.admin_scope import user_institution_abbr
from app.services.selection import (
    capacity_counts, capacity_of, mentor_confirm, mentor_invite, mentor_settings,
    student_choice_count, student_choose, student_settings, tenant_settings,
)


def proposed_card(db, user, target_id, content):
    text = content.casefold()
    if not target_id and not any(word in text for word in (
        "双选", "申请", "邀请", "确认", "选择", "apply", "invite", "confirm", "select",
    )):
        return None
    roles = {role.code for role in user.roles}
    if not roles.intersection(("student", "mentor")):
        return None
    student = "student" in roles
    school = user_institution_abbr(user)
    if not school:
        return None
    if student:
        role, profile, relation = "mentor", MentorProfile, User.mentor_profile
    else:
        role, profile, relation = "student", StudentProfile, User.student_profile
    stmt = select(User).where(User.tenant_id == user.tenant_id, User.id != user.id,
                              User.is_active.is_(True), User.roles.any(code=role),
                              relation.has(and_(profile.institution_abbr == school, profile.profile_completed_at.is_not(None))))
    if target_id:
        stmt = stmt.where(User.id == target_id)
    matches = [
        item for item in db.scalars(stmt)
        if target_id or (len(item.full_name) >= 2 and item.full_name.casefold() in text)
        or (item.username and item.username.casefold() in text)
    ]
    if len(matches) != 1:
        return None
    target = matches[0]
    settings = tenant_settings(db, user.tenant_id)
    if not settings.is_open:
        return None
    student_id, mentor_id = (user.id, target.id) if student else (target.id, user.id)
    pair = db.scalar(select(MentorSelection).where(MentorSelection.student_user_id == student_id,
                                                   MentorSelection.mentor_user_id == mentor_id))
    status = pair.status if pair else None
    if status == "confirmed" or db.scalar(select(MentorSelection.id).where(
        MentorSelection.student_user_id == student_id, MentorSelection.status == "confirmed",
    )):
        return None
    if (student and status == "pending_student") or (not student and status == "pending_mentor"):
        return None
    if not (student and status == "pending_mentor"):
        mentor = mentor_settings(db, mentor_id, settings.default_capacity)
        if not student or mentor.selection_mode == "first_come":
            if not mentor.is_exempt and sum(capacity_counts(db, mentor_id)) >= capacity_of(mentor, settings.default_capacity):
                return None
        if student:
            preferences = student_settings(db, student_id)
            limit = preferences.choice_limit or settings.default_student_choice_limit
            if not preferences.is_exempt and student_choice_count(db, student_id) >= limit:
                return None
    if student:
        action = "accept_invitation" if status == "pending_mentor" else "apply"
    else:
        action = "confirm_application" if status == "pending_student" else "invite"
    return {
        "kind": "mutual_selection", "action": action, "target_id": str(target.id),
        "target_name": target.full_name, "expected_status": status, "state": "ready",
    }


def execute_card(db, user, conversation, message_id):
    # Match the lock order used by all selection mutations.
    tenant_settings(db, user.tenant_id, lock=True)
    message = db.scalar(select(AiMessage).where(AiMessage.id == message_id,
        AiMessage.conversation_id == conversation.id, AiMessage.role == "assistant").with_for_update())
    if message is None or not message.action_card or message.action_card.get("kind") != "mutual_selection":
        raise HTTPException(404, detail={"code": "action_card_not_found"})
    card = message.action_card
    if card["state"] == "completed":
        return card
    target = UUID(card["target_id"])
    current = proposed_card(db, user, target, "")
    if not current or (current["action"], current["expected_status"]) != (card["action"], card["expected_status"]):
        raise HTTPException(409, detail={"code": "action_card_stale"})
    if card["action"] in ("apply", "accept_invitation"):
        item = student_choose(db, user, target, None)
    elif card["action"] == "confirm_application":
        pair_id = db.scalar(select(MentorSelection.id).where(
            MentorSelection.student_user_id == target, MentorSelection.mentor_user_id == user.id))
        item = mentor_confirm(db, user, pair_id, None)
    else:
        item = mentor_invite(db, user, target, None)
    result = {**card, "state": "completed", "selection_id": str(item.id), "result_status": item.status}
    message.action_card = result
    db.commit()
    return result
