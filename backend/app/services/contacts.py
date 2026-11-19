"""One-school contact permissions shared by people pages and AI context."""
from uuid import UUID
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from app.models.user import User
from app.services.admin_scope import is_administrator

CHANNELS = {"email": "email", "sms": "phone", "wechat": "wechat"}


def school(user: User) -> str | None:
    profile = user.student_profile or user.mentor_profile
    value = profile.institution_abbr if profile else None
    return value.strip().upper() if value and value.strip() else None


def load_contact(db: Session, viewer: User, target_id: UUID) -> User:
    target = db.scalar(select(User).options(selectinload(User.roles), selectinload(User.student_profile), selectinload(User.mentor_profile)).where(User.id == target_id, User.tenant_id == viewer.tenant_id, User.is_active.is_(True)))
    if target is None or not school(viewer) or school(viewer) != school(target):
        raise HTTPException(404, detail={"code": "contact_not_found"})
    if not any(role.code in {"student", "mentor"} for role in target.roles):
        raise HTTPException(404, detail={"code": "contact_not_found"})
    return target


def visible_contact(viewer: User, target: User) -> dict:
    same_school = bool(school(viewer)) and school(viewer) == school(target) and viewer.tenant_id == target.tenant_id and target.is_active
    result = {"user_id": str(target.id), "full_name": target.full_name}
    for field in CHANNELS.values():
        allowed = same_school and not is_administrator(target) and bool(getattr(target, f"share_{field}"))
        result[field] = getattr(target, field) if allowed else None
        result[f"{field}_visible"] = allowed
    return result


def draft_context(db: Session, viewer: User, target_id: UUID | None, channel: str | None) -> str:
    if target_id is None and channel is None:
        return ""
    if target_id is None or channel not in CHANNELS:
        raise HTTPException(422, detail={"code": "contact_channel_required"})
    target = load_contact(db, viewer, target_id)
    data = visible_contact(viewer, target)
    field = CHANNELS[channel]
    if not data[field]:
        raise HTTPException(403, detail={"code": "contact_hidden"})
    return (f"\nThe user explicitly selected a visible same-school contact for a {channel} draft. "
            f"Recipient name: {target.full_name}. Published {field}: {data[field]}. "
            "Draft only; never claim to have sent anything. Do not put the address, number or WeChat ID in the draft text. "
            "For email use a Subject: first line followed by a blank line and the body. Do not invent achievements or prior relationships.")


def redact_unshared(db: Session, viewer: User, text: list[str]) -> list[str]:
    # Re-evaluate on every request, including prior history after visibility changes.
    users = db.scalars(select(User).options(selectinload(User.student_profile), selectinload(User.mentor_profile)).where(User.tenant_id == viewer.tenant_id)).all()
    for target in users:
        data = visible_contact(viewer, target)
        for field in CHANNELS.values():
            value = getattr(target, field)
            if value and not data[field]:
                import re
                text = [re.sub(re.escape(value), "[contact not shared]", part, flags=re.IGNORECASE) for part in text]
                if field == "phone":
                    import phonenumbers
                    try:
                        parsed = phonenumbers.parse(value, None)
                        variants = {str(parsed.national_number), re.sub(r"\D", "", value), re.sub(r"\D", "", phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.NATIONAL))}
                        for digits in variants:
                            if len(digits) >= 6:
                                pattern = r"(?<!\d)\+?" + r"[\s().-]*".join(digits) + r"(?!\d)"
                                text = [re.sub(pattern, "[contact not shared]", part) for part in text]
                    except phonenumbers.NumberParseException:
                        pass
    return text
