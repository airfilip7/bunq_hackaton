"""FastAPI dependencies: user identity and storage."""

from functools import lru_cache

from backend.config import settings
from backend.storage.sqlite_store import SqliteStore, init_db


@lru_cache(maxsize=1)
def _get_store() -> SqliteStore:
    return init_db(settings.sqlite_path)


def get_storage() -> SqliteStore:
    return _get_store()


def get_user_id() -> str:
    """Return the current user id.

    bunq Nest runs inside the bunq app — the user is already authenticated.
    Identity is derived from the bunq API key used at deploy time.
    For the hackathon demo this is a fixed sandbox user.
    """
    return settings.demo_user_id
