from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash

from app.core.config import get_settings

password_hasher = PasswordHash.recommended()
_DUMMY_PASSWORD_HASH = password_hasher.hash("AcademicNexus-not-a-valid-password")
ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    """Store only a one-way Argon2id password hash / 仅保存 Argon2id 单向哈希。"""
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    # Verify a dummy hash for unknown accounts to reduce account-enumeration timing leaks.
    verified = password_hasher.verify(password, password_hash or _DUMMY_PASSWORD_HASH)
    return bool(password_hash) and verified


def create_access_token(*, subject: str, roles: list[str], auth_version: int = 0, scope: str = "authenticated") -> str:
    settings = get_settings()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload: dict[str, Any] = {
        "sub": subject,
        "roles": roles,
        # Incremented on password resets and account suspension so stolen or
        # previously issued tokens can be invalidated without rotating the
        # global signing key for every user.
        "auth_version": auth_version,
        "scope": scope,
        "exp": expires_at,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any] | None:
    try:
        return jwt.decode(
            token,
            get_settings().jwt_secret_key,
            algorithms=[ALGORITHM],
            options={"require": ["sub", "exp", "iat", "auth_version", "scope"]},
        )
    except InvalidTokenError:
        return None
