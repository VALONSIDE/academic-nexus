import time
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import httpx
import pytest
from app.core.config import get_settings
from app.db.base import Base
from app.models.ranking import RankingEmbedding, RankingRerankCache
from app.models.tenant import Tenant
from app.services import ranking
from app.services import ranking_provider as provider
from pydantic import SecretStr
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session


@pytest.fixture
def ranking_db(monkeypatch):
    monkeypatch.setattr(get_settings(), "siliconflow_api_key", SecretStr("test-key"))
    monkeypatch.setattr(ranking, "_blocked_until", 0)
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine, autoflush=False, expire_on_commit=False) as db:
        tenant = Tenant(slug="ranking", name="Ranking")
        db.add(tenant)
        db.commit()
        yield db, tenant.id
    engine.dispose()


def fake_provider(monkeypatch):
    calls = {"embeddings": 0, "rerank": 0}
    def embed(texts, deadline):
        calls["embeddings"] += 1
        return [[1.0, 0.0] + [0.0] * 1022 for _ in texts]
    def rerank(query, documents, deadline):
        calls["rerank"] += 1
        return [.99 if "language" in doc else .01 for doc in documents]
    monkeypatch.setattr(provider, "embeddings", embed)
    monkeypatch.setattr(provider, "rerank", rerank)
    return calls


def test_semantic_reorders_lexical_false_positive_and_caches(ranking_db, monkeypatch):
    db, tenant = ranking_db
    calls = fake_provider(monkeypatch)
    candidates = [ranking.Candidate("a", "ocean ecology", 90), ranking.Candidate("b", "language processing", 0)]
    first = ranking.rank(db, tenant, "text retrieval", candidates)
    db.commit()
    second = ranking.rank(db, tenant, "text retrieval", candidates)
    assert first == second and first.mode == "hybrid"
    assert first.scores["b"] > first.scores["a"]
    assert calls == {"embeddings": 1, "rerank": 1}
    candidates[1] = ranking.Candidate("b", "language understanding", 0)
    ranking.rank(db, tenant, "text retrieval", candidates)
    assert calls == {"embeddings": 2, "rerank": 2}


def test_cache_is_tenant_scoped_and_expiry_refreshes(ranking_db, monkeypatch):
    db, tenant = ranking_db
    calls = fake_provider(monkeypatch)
    candidates = [ranking.Candidate("a", "language research", 0)]
    ranking.rank(db, tenant, "text retrieval", candidates)
    other = Tenant(slug="other", name="Other")
    db.add(other); db.flush()
    ranking.rank(db, other.id, "text retrieval", candidates)
    assert calls == {"embeddings": 2, "rerank": 2}
    for model in (RankingEmbedding, RankingRerankCache):
        for row in db.scalars(select(model).where(model.tenant_id == tenant)):
            row.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db.flush()
    ranking.rank(db, tenant, "text retrieval", candidates)
    assert calls == {"embeddings": 3, "rerank": 3}


@pytest.mark.parametrize("stage,mode", [("embeddings", "local"), ("rerank", "semantic")])
def test_provider_failure_degrades_and_circuit_breaks(ranking_db, monkeypatch, stage, mode):
    db, tenant = ranking_db
    fake_provider(monkeypatch)
    def fail(*args):
        raise provider.RankingProviderError("provider_http_429")
    monkeypatch.setattr(provider, stage, fail)
    candidates = [ranking.Candidate("a", "language", 40)]
    assert ranking.rank(db, tenant, "research", candidates).mode == mode
    assert ranking.rank(db, tenant, "research", candidates).mode == "local"
    db.commit()
    assert db.scalar(select(Tenant.id)) == tenant


def test_empty_disabled_missing_key_and_busy_never_call_provider(ranking_db, monkeypatch):
    db, tenant = ranking_db
    calls = fake_provider(monkeypatch)
    candidates = [ranking.Candidate("a", "language", 40)]
    assert ranking.rank(db, tenant, "", candidates).mode == "local"
    monkeypatch.setattr(get_settings(), "ranking_enabled", False)
    assert ranking.rank(db, tenant, "research", candidates).mode == "local"
    monkeypatch.setattr(get_settings(), "ranking_enabled", True)
    monkeypatch.setattr(get_settings(), "siliconflow_api_key", SecretStr(""))
    assert ranking.rank(db, tenant, "research", candidates).mode == "local"
    monkeypatch.setattr(get_settings(), "siliconflow_api_key", SecretStr("test-key"))
    with ranking._slots, ranking._slots:
        assert ranking.rank(db, tenant, "research", candidates).mode == "local"
    assert calls == {"embeddings": 0, "rerank": 0}


def test_missing_cache_table_does_not_poison_transaction(ranking_db, monkeypatch):
    db, tenant = ranking_db
    fake_provider(monkeypatch)
    RankingEmbedding.__table__.drop(db.connection())
    result = ranking.rank(db, tenant, "research", [ranking.Candidate("a", "language", 40)])
    assert result.mode == "local"
    assert db.scalar(select(Tenant.id)) == tenant


def test_privacy_allowlist_and_unicode_limit():
    user = SimpleNamespace(full_name="Test Person", username="ID12345", email="student@example.test", phone="+8613812345678")
    profile = SimpleNamespace(research_interests=["Test Person language student@example.test ID12345 STU99 +8613812345678"],
                              student_no="STU99", academic_performance="Private grades", university="Private school")
    text = ranking.academic_text(profile, user)
    assert text == "language"
    assert len(ranking.clean_text("学术" * 3000).encode()) <= 1800


def test_candidate_and_batch_limits(ranking_db, monkeypatch):
    db, tenant = ranking_db
    calls = fake_provider(monkeypatch)
    monkeypatch.setattr(get_settings(), "ranking_candidate_limit", 10)
    monkeypatch.setattr(get_settings(), "ranking_rerank_limit", 3)
    result = ranking.rank(db, tenant, "query", [ranking.Candidate(str(n), f"language {n}", n) for n in range(20)])
    assert result.mode == "hybrid" and len(result.scores) == 20
    assert calls == {"embeddings": 1, "rerank": 4}


@pytest.mark.parametrize("body", [None, {}, {"results": [{"index": 0, "relevance_score": float("nan")}]},
    {"results": [{"index": True, "relevance_score": .5}]}, {"results": [{"index": 3, "relevance_score": .5}]}])
def test_rerank_rejects_invalid_responses(monkeypatch, body):
    monkeypatch.setattr(provider, "_post", lambda *args: body)
    with pytest.raises(provider.RankingProviderError, match="invalid_rerank"):
        provider.rerank("query", ["doc"], time.monotonic() + 10)


@pytest.mark.parametrize("vector", [[0.0] * 1024, [1.0], [float("inf")] * 1024, [True] * 1024])
def test_embedding_rejects_invalid_vectors(monkeypatch, vector):
    monkeypatch.setattr(provider, "_post", lambda *args: {"data": [{"index": 0, "embedding": vector}]})
    with pytest.raises(provider.RankingProviderError, match="invalid_embeddings"):
        provider.embeddings(["doc"], time.monotonic() + 10)


def test_provider_rest_contract_and_out_of_order_indices(monkeypatch):
    monkeypatch.setattr(get_settings(), "siliconflow_api_key", SecretStr("test-key"))
    def handler(request):
        assert request.headers["Authorization"] == "Bearer test-key"
        import json
        body = json.loads(request.content)
        assert body["model"] in {"BAAI/bge-m3", "BAAI/bge-reranker-v2-m3"}
        assert "dimensions" not in body
        if request.url.path.endswith("embeddings"):
            return httpx.Response(200, json={"data": [{"index": i, "embedding": [2.0] + [0.0] * 1023} for i in [1, 0]]})
        return httpx.Response(200, json={"results": [{"index": 1, "relevance_score": .9}, {"index": 0, "relevance_score": .1}]})
    factory = httpx.Client
    monkeypatch.setattr(provider.httpx, "Client", lambda **kwargs: factory(transport=httpx.MockTransport(handler), **kwargs))
    assert provider.embeddings(["a", "b"], time.monotonic() + 10)[0][0] == 1
    assert provider.rerank("q", ["a", "b"], time.monotonic() + 10) == [.1, .9]


@pytest.mark.parametrize("status", [301, 401, 429, 500])
def test_provider_http_failure_never_exposes_response_body(monkeypatch, status):
    monkeypatch.setattr(get_settings(), "siliconflow_api_key", SecretStr("test-key"))
    factory = httpx.Client
    monkeypatch.setattr(provider.httpx, "Client", lambda **kwargs: factory(
        transport=httpx.MockTransport(lambda request: httpx.Response(status, text="sensitive")), **kwargs))
    with pytest.raises(provider.RankingProviderError, match=f"^provider_http_{status}$"):
        provider.rerank("q", ["a"], time.monotonic() + 10)


def test_deadline_url_and_transport_failures(monkeypatch):
    with pytest.raises(provider.RankingProviderError, match="deadline_exceeded"):
        provider.rerank("q", ["a"], time.monotonic() - 1)
    monkeypatch.setattr(get_settings(), "siliconflow_api_key", SecretStr("test-key"))
    monkeypatch.setattr(get_settings(), "siliconflow_base_url", "https://untrusted.example/v1")
    with pytest.raises(provider.RankingProviderError, match="unsupported_provider_url"):
        provider.rerank("q", ["a"], time.monotonic() + 10)
    monkeypatch.setattr(get_settings(), "siliconflow_base_url", "https://api.siliconflow.cn/v1")
    factory = httpx.Client
    def fail(request):
        raise httpx.ReadTimeout("sensitive response")
    monkeypatch.setattr(provider.httpx, "Client", lambda **kwargs: factory(transport=httpx.MockTransport(fail), **kwargs))
    with pytest.raises(provider.RankingProviderError, match="^provider_unavailable$"):
        provider.rerank("q", ["a"], time.monotonic() + 10)


def test_duplicate_indices_are_rejected(monkeypatch):
    monkeypatch.setattr(provider, "_post", lambda *args: {"results": [
        {"index": 0, "relevance_score": .9}, {"index": 0, "relevance_score": .1}]})
    with pytest.raises(provider.RankingProviderError, match="invalid_rerank"):
        provider.rerank("q", ["a", "b"], time.monotonic() + 10)
