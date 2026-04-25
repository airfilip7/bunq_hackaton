"""FastAPI dependencies: auth and storage."""

from functools import lru_cache

import jwt
from fastapi import Header, HTTPException

from backend.config import settings
from backend.storage.sqlite_store import SqliteStore, init_db


@lru_cache(maxsize=1)
def _get_store() -> SqliteStore:
    return init_db(settings.sqlite_path)


def get_storage() -> SqliteStore:
    return _get_store()


def get_current_user_id(authorization: str = Header(...)) -> str:
    """Resolve the Authorization header to a user_id.

    # DEMO ONLY: 'Bearer demo' short-circuits JWT verification.
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")

    token = authorization.removeprefix("Bearer ")

    # DEMO ONLY — bypass JWT for demo flow
    if token == "demo":
        return settings.demo_user_id

    if not settings.jwt_secret:
        raise HTTPException(status_code=401, detail="JWT secret not configured")

    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user_id: str | None = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token missing sub claim")

    return user_id
