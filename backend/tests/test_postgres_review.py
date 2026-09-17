"""Opt-in checks against a disposable PostgreSQL; each test owns a random schema."""

from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
from threading import Barrier
import uuid

from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.base import Base
from app.models.ai import AiConversation
from app.models.resource import MentorResourceQuota
from app.models.tenant import Tenant
from app.models.user import User
from app.services.ai.quota import AiQuotaExceededError, quota_snapshot, reserve_ai_call, update_user_quota
from app.services.resources import reserve_file_bytes, update_quota

_url = os.environ.get("ACADEMICNEXUS_TEST_POSTGRES_URL")
pytestmark = pytest.mark.skipif(not _url, reason="Set ACADEMICNEXUS_TEST_POSTGRES_URL to a disposable PostgreSQL")


@pytest.fixture
def pg_engine():
    admin_engine = create_engine(_url)
    schema = "review_" + uuid.uuid4().hex
    with admin_engine.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public"))
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    url = make_url(_url).update_query_dict({"options": f"-csearch_path={schema},public"})
    engine = create_engine(url, connect_args={"options": f"-csearch_path={schema},public -cstatement_timeout=15000"})
    try:
        yield engine
    finally:
        engine.dispose()
        with admin_engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin_engine.dispose()


def seed(engine):
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        tenant = Tenant(slug="postgres-review", name="PostgreSQL Review")
        db.add(tenant)
        db.flush()
        user = User(tenant_id=tenant.id, username="PG_S1", full_name="Review", password_hash="hash")
        db.add(user)
        db.flush()
        conversation = AiConversation(tenant_id=tenant.id, user_id=user.id, topic="academic_planning", title="Test")
        db.add(conversation)
        db.commit()
        return user.id, conversation.id


def test_pgvector_ranking_persists_and_reuses_cache(pg_engine, monkeypatch):
    from pydantic import SecretStr
    from app.services import ranking, ranking_provider
    user_id, _ = seed(pg_engine)
    monkeypatch.setattr(get_settings(), "siliconflow_api_key", SecretStr("test-key"))
    monkeypatch.setattr(ranking, "_blocked_until", 0)
    calls = []
    def embeddings(texts, deadline):
        calls.append("embeddings")
        return [[1.0] + [0.0] * 1023 for _ in texts]
    def rerank(query, documents, deadline):
        calls.append("rerank")
        return [.9] * len(documents)
    monkeypatch.setattr(ranking_provider, "embeddings", embeddings)
    monkeypatch.setattr(ranking_provider, "rerank", rerank)
    for _ in range(2):
        with Session(pg_engine, autoflush=False, expire_on_commit=False) as db:
            tenant_id = db.get(User, user_id).tenant_id
            result = ranking.rank(db, tenant_id, "text research", [ranking.Candidate("a", "language", 60)])
            assert result.mode == "hybrid" and result.scores["a"] == 90
            db.commit()
    assert calls == ["embeddings", "rerank"]


def test_full_migration_chain_and_2gb_quota(pg_engine, monkeypatch):
    monkeypatch.setattr(get_settings(), "database_url", pg_engine.url.render_as_string(hide_password=False))
    backend = Path(__file__).resolve().parents[1]
    config = Config(str(backend / "alembic.ini"))
    config.set_main_option("script_location", str(backend / "alembic"))
    command.upgrade(config, "head")
    columns = {column["name"]: str(column["type"]) for column in inspect(pg_engine).get_columns("mentor_resource_quotas")}
    assert columns["quota_bytes"] == "BIGINT"
    assert columns["used_bytes"] == "BIGINT"
    user_id, _ = seed(pg_engine)
    with Session(pg_engine) as db:
        assert update_quota(db, user_id, 2048).quota_bytes == 2147483648
    # Downgrade is intentionally tested only while the stored values fit int32.
    with Session(pg_engine) as db:
        update_quota(db, user_id, 200)
    command.downgrade(config, "20260823_0013")
    command.upgrade(config, "head")


def test_concurrent_subscription_initialization(pg_engine):
    user_id, _ = seed(pg_engine)
    barrier = Barrier(2)

    def snapshot():
        with Session(pg_engine, autoflush=False, expire_on_commit=False) as db:
            barrier.wait(timeout=10)
            value = quota_snapshot(db, user_id)
            db.commit()
            return value.credit_balance

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert list(pool.map(lambda _: snapshot(), range(2))) == [10, 10]


def test_concurrent_ai_reservations_cannot_overspend(pg_engine):
    user_id, conversation_id = seed(pg_engine)
    with Session(pg_engine) as db:
        update_user_quota(db, user_id=user_id, credit_balance=1)
    barrier = Barrier(2)

    def reserve():
        with Session(pg_engine, autoflush=False, expire_on_commit=False) as db:
            user = db.get(User, user_id)
            barrier.wait(timeout=10)
            try:
                reserve_ai_call(db, user, conversation_id)
                return "reserved"
            except AiQuotaExceededError as error:
                db.rollback()
                return error.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(lambda _: reserve(), range(2))) == ["credit_balance_exhausted", "reserved"]


def test_concurrent_first_resource_reservations_are_accumulated(pg_engine):
    user_id, _ = seed(pg_engine)
    barrier = Barrier(2)

    def reserve():
        with Session(pg_engine, autoflush=False, expire_on_commit=False) as db:
            barrier.wait(timeout=10)
            reserve_file_bytes(db, user_id, 1024)
            db.commit()

    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(lambda _: reserve(), range(2)))
    with Session(pg_engine) as db:
        assert db.scalar(select(MentorResourceQuota.used_bytes).where(MentorResourceQuota.user_id == user_id)) == 2048


def test_concurrent_first_selection_settings(pg_engine):
    from app.services.selection import mentor_settings, student_settings, tenant_settings

    user_id, _ = seed(pg_engine)
    with Session(pg_engine) as db:
        tenant_id = db.get(User, user_id).tenant_id
    barrier = Barrier(2)

    def settings():
        with Session(pg_engine, autoflush=False) as db:
            barrier.wait(timeout=10)
            result = (tenant_settings(db, tenant_id, lock=True).id,
                      mentor_settings(db, user_id, 5, lock=True).id,
                      student_settings(db, user_id, lock=True).id)
            db.commit()
            return result

    with ThreadPoolExecutor(max_workers=2) as pool:
        first, second = pool.map(lambda _: settings(), range(2))
    assert first == second
