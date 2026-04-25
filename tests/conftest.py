import pytest
from fastapi.testclient import TestClient

from backend.deps import get_storage
from backend.main import app
from backend.storage.sqlite_store import SqliteStore, init_db


@pytest.fixture()
def store(tmp_path) -> SqliteStore:
    """Fresh SQLite store for each test."""
    return init_db(str(tmp_path / "test.db"))


@pytest.fixture()
def client(store) -> TestClient:
    """TestClient wired to a fresh store per test."""
    app.dependency_overrides[get_storage] = lambda: store
    yield TestClient(app)
    app.dependency_overrides.clear()
