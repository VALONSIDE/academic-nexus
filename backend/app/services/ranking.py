"""Bounded semantic ranking with tenant-scoped caches and deterministic fallback."""

import hashlib
import json
import logging
import re
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import get_settings
from app.models.ranking import RankingEmbedding, RankingRerankCache
from app.services import ranking_provider as provider

ALGORITHM_VERSION = "siliconflow-hybrid-v2"
_slots = threading.BoundedSemaphore(2)
_logger = logging.getLogger(__name__)
_blocked_until = 0.0


@dataclass(frozen=True)
class Candidate:
    id: str
    text: str
    lexical_score: int


@dataclass(frozen=True)
class RankingResult:
    scores: dict[str, int]
    mode: str = "local"


def academic_text(profile, user=None) -> str:
    """Allowlist academic fields; exclude identity and administrative fields."""
    fields = ("research_interests", "skills", "academic_goals", "research_experience",
              "research_directions", "representative_papers", "research_projects", "mentoring_style")
    values = []
    for field in fields:
        value = getattr(profile, field, None)
        if value:
            values.append("; ".join(value) if isinstance(value, list) else str(value))
    text = "\n".join(values)
    for field in ("student_no", "employee_no"):
        value = getattr(profile, field, None)
        if value:
            text = text.replace(value, " ")
    return clean_text(text, user)


def clean_text(text: str, user=None) -> str:
    if user is not None:
        for field in ("full_name", "username", "email", "phone"):
            value = getattr(user, field, None)
            if value:
                text = re.sub(re.escape(str(value)), " ", text, flags=re.IGNORECASE)
    text = re.sub(r"https?://\S+|[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}|(?<!\w)\+?\d[\d ()-]{6,}\d", " ", text)
    # Conservative byte cap keeps Chinese and English inside rerank token limits.
    return " ".join(text.split()).encode("utf-8")[:1800].decode("utf-8", errors="ignore")


def _fingerprint(kind, value):
    settings = get_settings()
    data = [ALGORITHM_VERSION, kind, settings.siliconflow_embedding_model, settings.siliconflow_rerank_model, value]
    return hashlib.sha256(json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def _save(db, model, tenant_id, fingerprint, expires_at, **values):
    insert = pg_insert if db.get_bind().dialect.name == "postgresql" else sqlite_insert
    statement = insert(model).values(tenant_id=tenant_id, fingerprint=fingerprint, expires_at=expires_at, **values)
    db.execute(statement.on_conflict_do_update(index_elements=["tenant_id", "fingerprint"],
                                               set_={"expires_at": expires_at, **values}))


def rank(db, tenant_id, query: str, candidates: list[Candidate]) -> RankingResult:
    try:
        with db.begin_nested():
            return _rank(db, tenant_id, query, candidates)
    except SQLAlchemyError:
        _logger.warning("Ranking fallback: cache_unavailable")
        return RankingResult({item.id: item.lexical_score for item in candidates})


def _rank(db, tenant_id, query: str, candidates: list[Candidate]) -> RankingResult:
    global _blocked_until
    settings = get_settings()
    local = RankingResult({item.id: item.lexical_score for item in candidates})
    query = clean_text(query)
    if not candidates or not query or not settings.ranking_enabled or not settings.siliconflow_api_key.get_secret_value():
        return local
    if time.monotonic() < _blocked_until or not _slots.acquire(blocking=False):
        return local
    deadline = time.monotonic() + settings.ranking_timeout_seconds
    now = datetime.now(timezone.utc)
    # Bound cost independently of the number of users/resources in a tenant.
    pool = sorted((item for item in candidates if item.text), key=lambda item: (-item.lexical_score, item.id))[:settings.ranking_candidate_limit]
    if not pool:
        _slots.release()
        return local
    semantic = None
    try:
        texts = { _fingerprint("embedding", text): text for text in [query] + [clean_text(item.text) for item in pool] }
        vectors = {row.fingerprint: list(row.embedding) for row in db.scalars(select(RankingEmbedding).where(
            RankingEmbedding.tenant_id == tenant_id, RankingEmbedding.fingerprint.in_(texts), RankingEmbedding.expires_at > now))}
        missing = [key for key in texts if key not in vectors]
        for start in range(0, len(missing), 32):
            batch = missing[start:start + 32]
            values = provider.embeddings([texts[key] for key in batch], deadline)
            for key, vector in zip(batch, values, strict=True):
                vectors[key] = vector
                _save(db, RankingEmbedding, tenant_id, key, now + timedelta(days=settings.ranking_embedding_ttl_days), embedding=vector)
        query_vector = vectors[_fingerprint("embedding", query)]
        keys = [_fingerprint("embedding", clean_text(item.text)) for item in pool]
        if db.get_bind().dialect.name == "postgresql":
            similarities = dict(db.execute(select(RankingEmbedding.fingerprint,
                (1 - RankingEmbedding.embedding.cosine_distance(query_vector))).where(
                    RankingEmbedding.tenant_id == tenant_id, RankingEmbedding.fingerprint.in_(keys))).all())
        else:
            similarities = {key: sum(a * b for a, b in zip(query_vector, vectors[key], strict=True)) for key in keys}
        cosine = {item.id: max(0.0, min(1.0, float(similarities[key]))) for item, key in zip(pool, keys, strict=True)}
        # Unrecalled tail has only its lexical contribution; all recalled items are reranked.
        scores = {item.id: round(item.lexical_score * .05) for item in candidates}
        scores.update({item.id: round(95 * cosine[item.id] + .05 * item.lexical_score) for item in pool})
        semantic = RankingResult(scores, "semantic")
        pool.sort(key=lambda item: (-scores[item.id], item.id))
        final = dict(scores)
        for start in range(0, len(pool), settings.ranking_rerank_limit):
            batch = pool[start:start + settings.ranking_rerank_limit]
            documents = [clean_text(item.text) for item in batch]
            key = _fingerprint("rerank", [query, documents])
            cached = db.scalar(select(RankingRerankCache).where(RankingRerankCache.tenant_id == tenant_id,
                RankingRerankCache.fingerprint == key, RankingRerankCache.expires_at > now))
            relevance = cached.scores if cached is not None else provider.rerank(query, documents, deadline)
            if cached is None:
                _save(db, RankingRerankCache, tenant_id, key, now + timedelta(seconds=settings.ranking_cache_ttl_seconds), scores=relevance)
            for item, value in zip(batch, relevance, strict=True):
                final[item.id] = round(80 * value + 15 * cosine[item.id] + .05 * item.lexical_score)
        for model in (RankingEmbedding, RankingRerankCache):
            db.execute(delete(model).where(model.tenant_id == tenant_id, model.expires_at <= now)
                       .execution_options(synchronize_session=False))
        return RankingResult(final, "hybrid")
    except provider.RankingProviderError as error:
        _blocked_until = time.monotonic() + 30
        _logger.warning("Ranking fallback: %s", str(error))
        return semantic or local
    finally:
        _slots.release()
