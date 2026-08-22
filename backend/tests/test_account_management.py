import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.api.v1.endpoints.auth import change_own_password
from app.core.security import hash_password, verify_password
from app.db.base import Base
from app.models import tenant, user  # noqa: F401
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.auth import PasswordChangeRequest


def test_authenticated_user_can_change_only_their_own_password() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        organization = Tenant(slug="account-test", name="Account Test")
        db.add(organization)
        db.flush()
        account = User(
            tenant_id=organization.id,
            username="TEST_S1",
            full_name="Test User",
            password_hash=hash_password("CurrentPassword2026"),
        )
        db.add(account)
        db.commit()

        change_own_password(
            PasswordChangeRequest(current_password="CurrentPassword2026", new_password="ChangedPassword2026"),
            account,
            db,
        )
        assert verify_password("ChangedPassword2026", account.password_hash)
        with pytest.raises(HTTPException, match="400"):
            change_own_password(
                PasswordChangeRequest(current_password="WrongPassword2026", new_password="AnotherPassword2026"),
                account,
                db,
            )
