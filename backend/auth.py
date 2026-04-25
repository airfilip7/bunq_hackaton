"""JWT authentication dependency for FastAPI.

In production: verifies Cognito-issued JWT (RS256), extracts `sub` as user_id.
In dev mode (cognito_user_pool_id is empty): accepts `X-Dev-User-Id` header instead.
Either way, missing/invalid credentials → HTTP 401.
"""
import logging

import httpx
from fastapi import Depends, Header, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from backend.config import settings

logger = logging.getLogger(__name__)

_bearer = HTTPBearer(auto_error=False)

# Module-level JWKS cache (fetched once per process).
_jwks: dict | None = None


def _get_jwks() -> dict:
    global _jwks
    if _jwks is None:
        url = (
            f"https://cognito-idp.{settings.cognito_region}.amazonaws.com"
            f"/{settings.cognito_user_pool_id}/.well-known/jwks.json"
        )
        resp = httpx.get(url, timeout=5)
        resp.raise_for_status()
        _jwks = resp.json()
    return _jwks


def get_current_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    x_dev_user_id: str | None = Header(default=None),
) -> str:
    """FastAPI dependency. Returns user_id or raises HTTP 401."""
    # Dev bypass: only when Cognito pool is not configured.
    if not settings.cognito_user_pool_id:
        if not x_dev_user_id:
            raise HTTPException(status_code=401, detail="X-Dev-User-Id header required in dev mode")
        return x_dev_user_id

    # Production path: validate Bearer JWT.
    if credentials is None:
        raise HTTPException(status_code=401, detail="Authorization header missing")

    token = credentials.credentials
    try:
        jwks = _get_jwks()
        claims = jwt.decode(
            token,
            jwks,
            algorithms=["RS256"],
            audience=settings.cognito_user_pool_id,
            options={"verify_at_hash": False},
        )
        user_id: str = claims["sub"]
        return user_id
    except JWTError as exc:
        logger.warning("JWT validation failed: %s", exc)
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc
    except Exception as exc:
        logger.error("Unexpected auth error: %s", exc)
        raise HTTPException(status_code=401, detail="Authentication error") from exc
