"""Run tests with disposable configuration, without reading the private .env."""

from unittest.mock import patch

from app.core.config import Settings


_settings = Settings(
    _env_file=None,
    app_env="test",
    database_url="sqlite+pysqlite:///:memory:",
    jwt_secret_key="test-only-jwt-secret-key-at-least-32-characters",
    access_key_pepper="test-only-access-key-pepper-at-least-32-characters",
    initial_admin_email="admin@example.test",
    initial_admin_password="TestOnlyPassword2026",
    minimax_api_key="",
    siliconflow_api_key="",
    ai_daily_project_limit=500,
    ai_default_daily_user_limit=10,
    ai_default_credit_balance=10,
    mentor_resource_default_quota_mb=200,
)
_settings_patch = patch("app.core.config.get_settings", return_value=_settings)
_settings_patch.start()


def pytest_unconfigure(config):
    _settings_patch.stop()
