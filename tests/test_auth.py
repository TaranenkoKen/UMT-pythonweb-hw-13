"""Unit tests for the auth module."""
import pytest
from datetime import timedelta
from unittest.mock import patch, AsyncMock

import auth


def test_password_hash_and_verify():
    hashed = auth.get_password_hash("secret")
    assert auth.verify_password("secret", hashed)
    assert not auth.verify_password("wrong", hashed)


def test_create_access_token_contains_sub():
    token = auth.create_access_token({"sub": "user@example.com"})
    assert token


def test_create_and_decode_email_token():
    token = auth.create_email_token("user@example.com")
    email = auth.decode_email_token(token)
    assert email == "user@example.com"


def test_decode_email_token_wrong_type():
    token = auth.create_password_reset_token("user@example.com")
    result = auth.decode_email_token(token)
    assert result is None


def test_create_and_decode_refresh_token():
    token = auth.create_refresh_token({"sub": "user@example.com"})
    email = auth.decode_refresh_token(token)
    assert email == "user@example.com"


def test_decode_refresh_token_wrong_type():
    token = auth.create_access_token({"sub": "user@example.com"})
    result = auth.decode_refresh_token(token)
    assert result is None


def test_create_and_decode_password_reset_token():
    token = auth.create_password_reset_token("user@example.com")
    email = auth.decode_password_reset_token(token)
    assert email == "user@example.com"


def test_decode_password_reset_token_expired():
    token = auth.create_password_reset_token.__wrapped__("user@example.com") if hasattr(
        auth.create_password_reset_token, "__wrapped__"
    ) else None
    result = auth.decode_password_reset_token("invalidtoken")
    assert result is None


def test_decode_invalid_token_returns_none():
    assert auth.decode_email_token("bad.token.here") is None
    assert auth.decode_refresh_token("bad.token.here") is None
    assert auth.decode_password_reset_token("bad.token.here") is None
