from app.core.security import create_access_token, decode_access_token, hash_password, verify_password


def test_password_hash_is_one_way_and_verifiable() -> None:
    raw_password = "AcademicNexus2026Secure"
    password_hash = hash_password(raw_password)
    assert password_hash != raw_password
    assert verify_password(raw_password, password_hash)
    assert not verify_password("incorrect-password", password_hash)


def test_access_token_contains_subject_and_roles() -> None:
    token = create_access_token(subject="3d3f57c3-ea31-4f67-a0b3-4f1d933e8a86", roles=["student"])
    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == "3d3f57c3-ea31-4f67-a0b3-4f1d933e8a86"
    assert payload["roles"] == ["student"]
