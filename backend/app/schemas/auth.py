import re
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


Locale = Literal["zh-CN", "en-US"]
USERNAME_PATTERN = re.compile(r"^[A-Z0-9]{2,12}_[ST][A-Z0-9_-]{2,64}$")
ACCESS_KEY_PATTERN = re.compile(r"^\d{4}-[A-Z]{4}-\d{4}-\d{4}$")


def validate_password_strength(password: str) -> str:
    """Apply the password policy without retaining the plaintext password."""
    has_upper = any(character.isupper() for character in password)
    has_lower = any(character.islower() for character in password)
    has_digit = any(character.isdigit() for character in password)
    if not (has_upper and has_lower and has_digit):
        raise ValueError("Password must include uppercase, lowercase, and a number / 密码须含大小写字母和数字")
    return password


class ActivationRequest(BaseModel):
    """Activation is allowed only for imported partner-school identities / 仅允许激活合作院校导入的身份。"""

    username: str = Field(min_length=7, max_length=100)
    full_name: str = Field(min_length=2, max_length=120)
    academic_id: str = Field(min_length=2, max_length=64)
    access_key: str = Field(min_length=19, max_length=19)
    password: str = Field(min_length=12, max_length=128)
    preferred_locale: Locale = "zh-CN"
    terms_accepted: Literal[True]
    privacy_accepted: Literal[True]

    @field_validator("username")
    @classmethod
    def validate_username(cls, username: str) -> str:
        normalized = username.strip().upper()
        if not USERNAME_PATTERN.fullmatch(normalized):
            raise ValueError("Invalid username format / 用户名格式不正确")
        return normalized

    @field_validator("academic_id")
    @classmethod
    def normalize_academic_id(cls, academic_id: str) -> str:
        return academic_id.strip().upper()

    @field_validator("access_key")
    @classmethod
    def validate_access_key(cls, access_key: str) -> str:
        normalized = access_key.strip().upper()
        if not ACCESS_KEY_PATTERN.fullmatch(normalized):
            raise ValueError("Invalid Access Key format / Access Key 格式不正确")
        return normalized

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, password: str) -> str:
        has_upper = any(character.isupper() for character in password)
        has_lower = any(character.islower() for character in password)
        has_digit = any(character.isdigit() for character in password)
        if not (has_upper and has_lower and has_digit):
            raise ValueError("Password must include uppercase, lowercase, and a number / 密码须含大小写字母和数字")
        return password


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=128)


class LocaleUpdateRequest(BaseModel):
    preferred_locale: Locale


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=12, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, password: str) -> str:
        return validate_password_strength(password)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    full_name: str
    preferred_locale: Locale
    is_active: bool
    roles: list[str]


class AuthResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    user: UserResponse


class ActivationStartResponse(BaseModel):
    """A limited token can submit only the mandatory Phase 2 portrait."""

    registration_token: str
    token_type: Literal["bearer"] = "bearer"
    role: Literal["student", "mentor"]
