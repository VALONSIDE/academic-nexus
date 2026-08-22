"""Access Key generation and verification / Access Key 生成与校验。"""

import hashlib
import hmac
import re
import secrets

from app.core.config import get_settings

ACCESS_KEY_PATTERN = re.compile(r"^\d{4}-[A-Z]{4}-\d{4}-\d{4}$")
_DIGITS = "0123456789"
_UPPERCASE = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def normalize_access_key(access_key: str) -> str:
    """Normalize only harmless presentation differences / 仅规范化大小写和首尾空格。"""
    return access_key.strip().upper()


def access_key_fingerprint(access_key: str) -> str:
    """Stable keyed fingerprint used only for uniqueness enforcement / 用于唯一约束的带密钥指纹。"""
    canonical_key = normalize_access_key(access_key).encode("utf-8")
    pepper = get_settings().access_key_pepper.encode("utf-8")
    return hmac.new(pepper, canonical_key, hashlib.sha256).hexdigest()


def generate_access_key() -> str:
    """Generate 59-bit CSPRNG code: XXXX-ABCD-XXXX-XXXX / 生成密码学随机激活码。"""
    first = "".join(secrets.choice(_DIGITS) for _ in range(4))
    letters = "".join(secrets.choice(_UPPERCASE) for _ in range(4))
    last = "".join(secrets.choice(_DIGITS) for _ in range(8))
    return f"{first}-{letters}-{last[:4]}-{last[4:]}"


def is_valid_access_key_format(access_key: str) -> bool:
    return bool(ACCESS_KEY_PATTERN.fullmatch(normalize_access_key(access_key)))
