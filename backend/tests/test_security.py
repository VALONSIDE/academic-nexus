import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.v1.endpoints.auth import read_me, update_contact
from app.core.security import create_access_token, decode_access_token, hash_password, verify_password
from app.db.base import Base
from app.models import tenant, user  # noqa: F401
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.auth import ContactUpdateRequest


def test_password_hash_is_one_way_and_verifiable() -> None:
    raw_password = "AcademicNexus2026Secure"
    password_hash = hash_password(raw_password)
    assert password_hash != raw_password
    assert verify_password(raw_password, password_hash)
    assert not verify_password("incorrect-password", password_hash)


def test_access_token_contains_subject_roles_and_auth_version() -> None:
    token = create_access_token(subject="3d3f57c3-ea31-4f67-a0b3-4f1d933e8a86", roles=["student"], auth_version=7)
    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == "3d3f57c3-ea31-4f67-a0b3-4f1d933e8a86"
    assert payload["roles"] == ["student"]
    assert payload["auth_version"] == 7


def test_password_or_account_security_changes_revoke_prior_tokens() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        organization = Tenant(slug="token-revocation", name="Token Revocation")
        db.add(organization)
        db.flush()
        account = User(
            tenant_id=organization.id,
            username="TEST_S2",
            full_name="Token User",
            password_hash=hash_password("AcademicNexus2026Secure"),
        )
        db.add(account)
        db.commit()

        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=create_access_token(subject=str(account.id), roles=["student"], auth_version=account.auth_version),
        )
        assert get_current_user(credentials, db).id == account.id

        account.auth_version += 1
        db.commit()
        with pytest.raises(HTTPException, match="401"):
            get_current_user(credentials, db)


def test_user_can_read_and_update_their_own_contact_details() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        organization = Tenant(slug="contact-phone", name="Contact Phone")
        db.add(organization)
        db.flush()
        account = User(
            tenant_id=organization.id,
            username="PHONE_S1",
            full_name="Phone User",
            password_hash="hash",
            phone="+861012345678",
            email="phone.user@example.edu",
        )
        db.add(account)
        db.commit()

        assert read_me(account).email == "phone.user@example.edu"
        updated = update_contact(ContactUpdateRequest(phone="+86 138 0013 8000", email="Phone.User+new@Example.edu"), account, db)
        assert updated.phone == "+8613800138000"
        assert updated.email == "phone.user+new@example.edu"
        saved = db.get(User, account.id)
        assert saved is not None and saved.phone == "+8613800138000" and saved.email == "phone.user+new@example.edu"

        other = User(tenant_id=organization.id, username="PHONE_S2", full_name="Other User", password_hash="hash", email="existing@example.edu")
        db.add(other)
        db.commit()
        with pytest.raises(HTTPException) as conflict:
            update_contact(ContactUpdateRequest(email="Existing@Example.edu"), account, db)
        assert conflict.value.status_code == 409
