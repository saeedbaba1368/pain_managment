"""Unit tests for core/security.py -- no database required."""
from __future__ import annotations

import time

import pytest
from jose import JWTError


def test_hash_password_produces_different_hash_each_time():
    from core.security import hash_password

    h1 = hash_password("correct horse battery staple")
    h2 = hash_password("correct horse battery staple")
    # bcrypt salts each hash independently -- two hashes of the same
    # password must never be equal, or salting isn't actually happening.
    assert h1 != h2


def test_verify_password_roundtrip():
    from core.security import hash_password, verify_password

    hashed = hash_password("S3cur3P@ssword!")
    assert verify_password("S3cur3P@ssword!", hashed) is True
    assert verify_password("wrong-password", hashed) is False


def test_verify_password_never_raises_on_malformed_hash():
    from core.security import verify_password

    # A malformed/garbage hash must fail closed (return False), not
    # raise -- this sits directly on the login code path.
    assert verify_password("anything", "not-a-real-bcrypt-hash") is False
    assert verify_password("anything", "") is False


def test_access_token_roundtrip():
    from core.security import create_access_token, decode_token

    token = create_access_token(subject="42", role="doctor")
    payload = decode_token(token)
    assert payload["sub"] == "42"
    assert payload["role"] == "doctor"
    assert payload["type"] == "access"


def test_refresh_token_has_no_role_claim():
    from core.security import create_refresh_token, decode_token

    token = create_refresh_token(subject="42")
    payload = decode_token(token)
    assert payload["type"] == "refresh"
    assert "role" not in payload


def test_decode_token_rejects_garbage():
    from core.security import decode_token

    with pytest.raises(JWTError):
        decode_token("not.a.valid.jwt")


def test_expired_access_token_is_rejected():
    from datetime import timedelta

    from core.security import create_access_token, decode_token

    token = create_access_token(subject="1", role="admin", expires_delta=timedelta(seconds=-1))
    with pytest.raises(JWTError):
        decode_token(token)


def test_encrypted_string_field_roundtrips_via_fernet():
    """EncryptedString is a SQLAlchemy TypeDecorator; exercise its bind/result
    hooks directly rather than requiring a live database."""
    from core.security import EncryptedString

    col = EncryptedString(255)
    ciphertext = col.process_bind_param("0123456789", dialect=None)
    assert ciphertext != "0123456789"  # actually encrypted, not passed through

    plaintext = col.process_result_value(ciphertext, dialect=None)
    assert plaintext == "0123456789"


def test_encrypted_string_passes_through_none():
    from core.security import EncryptedString

    col = EncryptedString(255)
    assert col.process_bind_param(None, dialect=None) is None
    assert col.process_result_value(None, dialect=None) is None
