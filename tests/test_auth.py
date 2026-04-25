import time

import jwt as pyjwt
import pytest

from backend.config import settings
from backend.deps import get_current_user_id


def test_demo_token_returns_demo_user():
    user_id = get_current_user_id(authorization="Bearer demo")
    assert user_id == settings.demo_user_id


def test_missing_bearer_prefix_raises():
    with pytest.raises(Exception) as exc_info:
        get_current_user_id(authorization="Token abc")
    assert exc_info.value.status_code == 401


def test_empty_bearer_raises():
    with pytest.raises(Exception) as exc_info:
        get_current_user_id(authorization="NotBearer")
    assert exc_info.value.status_code == 401


def test_valid_jwt(monkeypatch):
    secret = "test-secret-key"
    monkeypatch.setattr(settings, "jwt_secret", secret)

    token = pyjwt.encode(
        {"sub": "user_123", "exp": int(time.time()) + 3600},
        secret,
        algorithm="HS256",
    )
    user_id = get_current_user_id(authorization=f"Bearer {token}")
    assert user_id == "user_123"


def test_expired_jwt_raises(monkeypatch):
    secret = "test-secret-key"
    monkeypatch.setattr(settings, "jwt_secret", secret)

    token = pyjwt.encode(
        {"sub": "user_123", "exp": int(time.time()) - 10},
        secret,
        algorithm="HS256",
    )
    with pytest.raises(Exception) as exc_info:
        get_current_user_id(authorization=f"Bearer {token}")
    assert exc_info.value.status_code == 401
    assert "expired" in str(exc_info.value.detail).lower()


def test_jwt_missing_sub_raises(monkeypatch):
    secret = "test-secret-key"
    monkeypatch.setattr(settings, "jwt_secret", secret)

    token = pyjwt.encode(
        {"exp": int(time.time()) + 3600},
        secret,
        algorithm="HS256",
    )
    with pytest.raises(Exception) as exc_info:
        get_current_user_id(authorization=f"Bearer {token}")
    assert exc_info.value.status_code == 401
    assert "sub" in str(exc_info.value.detail).lower()


def test_jwt_without_secret_configured_raises(monkeypatch):
    monkeypatch.setattr(settings, "jwt_secret", "")

    with pytest.raises(Exception) as exc_info:
        get_current_user_id(authorization="Bearer some.jwt.token")
    assert exc_info.value.status_code == 401
