"""Shared database rate limits and credential-free administrator audit trail."""
import hashlib
import hmac
import time
import socket
import ipaddress
from uuid import UUID

from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.core.config import get_settings
from app.core.security import decode_access_token
from app.db.session import SessionLocal
from app.models.security import SecurityAudit, SecurityRateBucket
from app.models.user import User


def rate_allowed(peer: str, path: str) -> bool:
    window = int(time.time() // 60)
    key = hmac.new(get_settings().access_key_pepper.encode(), f"{peer}:{path}".encode(), hashlib.sha256).hexdigest()
    with SessionLocal() as db:
        insert = pg_insert if db.get_bind().dialect.name == "postgresql" else sqlite_insert
        statement = insert(SecurityRateBucket).values(key=key, window=window, count=1)
        count = db.scalar(statement.on_conflict_do_update(index_elements=["key", "window"], set_={"count": SecurityRateBucket.count + 1}).returning(SecurityRateBucket.count))
        db.execute(delete(SecurityRateBucket).where(SecurityRateBucket.window < window - 2))
        db.commit()
        return count <= (30 if path == "/ai/messages" else 10 if path.endswith("/login") else 5)


def begin_audit(token: str, method: str, path: str):
    payload = decode_access_token(token)
    actor = tenant = None
    with SessionLocal() as db:
        if payload and payload.get("scope") == "authenticated":
            try:
                user = db.get(User, UUID(payload["sub"]))
            except (ValueError, TypeError):
                user = None
            if user and user.is_active and user.auth_version == payload.get("auth_version"):
                actor, tenant = user.id, user.tenant_id
        event = SecurityAudit(actor_id=actor, tenant_id=tenant, method=method, path=path[:255], status=0)
        db.add(event)
        db.commit()
        return event.id


def finish_audit(event_id, status: int):
    with SessionLocal() as db:
        event = db.get(SecurityAudit, event_id)
        event.status = status
        db.commit()


def client_peer(peer: str, forwarded: str) -> str:
    # Trust only the actual Compose Nginx peer, never arbitrary forwarded headers.
    try:
        nginx_addresses = {result[4][0] for result in socket.getaddrinfo("nginx", None)}
        if peer in nginx_addresses and forwarded:
            return str(ipaddress.ip_address(forwarded))
    except (OSError, ValueError):
        pass
    return peer
