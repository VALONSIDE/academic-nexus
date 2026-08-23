"""Cryptographically-safe premium subscription-key generation and verification."""

import hashlib
import hmac
import re
import secrets

from app.core.config import get_settings

SUBSCRIPTION_KEY_PATTERN = re.compile(r"^[A-Z0-9]{2}-[PUM]-[A-Z0-9]{4}-[A-Z0-9]{3}$")
_ALPHANUMERIC = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
_PLAN_MARKERS = {"pro": "P", "ultra": "U", "max": "M"}


def normalize_subscription_key(value: str) -> str:
    return value.strip().upper()


def is_valid_subscription_key_format(value: str) -> bool:
    return bool(SUBSCRIPTION_KEY_PATTERN.fullmatch(normalize_subscription_key(value)))


def subscription_key_fingerprint(value: str) -> str:
    canonical = normalize_subscription_key(value).encode("utf-8")
    pepper = get_settings().access_key_pepper.encode("utf-8")
    return hmac.new(pepper, canonical, hashlib.sha256).hexdigest()


def generate_subscription_key(plan_code: str) -> str:
    """Return the requested ``XX-X-XXXX-XXX`` CSPRNG key format.

    The middle marker makes receipts easier to sort without weakening the seven
    random base-32-like characters.  Its HMAC fingerprint is still protected by
    a unique database constraint and generation retries on collision.
    """
    marker = _PLAN_MARKERS[plan_code]
    choose = lambda length: "".join(secrets.choice(_ALPHANUMERIC) for _ in range(length))
    return f"{choose(2)}-{marker}-{choose(4)}-{choose(3)}"
