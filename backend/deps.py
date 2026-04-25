"""FastAPI dependencies: auth and storage."""

from functools import lru_cache

from backend.bunq_client import BunqClient, get_bunq_client as _factory
from backend.config import settings
from backend.storage.sqlite_store import SqliteStore, init_db


@lru_cache(maxsize=1)
def _get_store() -> SqliteStore:
    return init_db(settings.sqlite_path)


def get_storage() -> SqliteStore:
    return _get_store()


@lru_cache(maxsize=1)
def _get_bunq_client() -> BunqClient:
    return _factory()


def get_bunq_client() -> BunqClient:
    return _get_bunq_client()
