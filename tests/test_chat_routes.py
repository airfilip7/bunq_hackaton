"""Integration tests for backend/routes/chat.py — Phase 8 Task 4."""

from __future__ import annotations

import json
import time
from unittest.mock import AsyncMock, patch

import pytest
import ulid

from backend.models import Turn


# ── SSE parsing helper ────────────────────────────────────────────────────────


def parse_sse_events(body: str) -> list[dict]:
    """Parse SSE response body into list of {event, data} dicts.

    Handles both \\n and \\r\\n line endings.
    """
    events = []
    current_event = None
    current_data = None
    for line in body.splitlines():
        line = line.strip()
        if line.startswith("event:"):
            current_event = line[len("event:"):].strip()
        elif line.startswith("data:"):
            current_data = line[len("data:"):].strip()
        elif line == "" and current_event and current_data:
            events.append({"event": current_event, "data": json.loads(current_data)})
            current_event = None
            current_data = None
    # Flush last event if body doesn't end with blank line
    if current_event and current_data:
        events.append({"event": current_event, "data": json.loads(current_data)})
    return events


# ── Fixtures ──────────────────────────────────────────────────────────────────

AUTH = {"Authorization": "Bearer demo"}
DEMO_USER = "u_demo"


def make_turn(session_id: str, **kwargs) -> Turn:
    return Turn(
        turn_id=str(ulid.ULID()),
        session_id=session_id,
        ts_ms=int(time.time() * 1000),
        **kwargs,
    )


# ── GET /chat/sessions ────────────────────────────────────────────────────────


def test_list_sessions_empty(client):
    resp = client.get("/chat/sessions", headers=AUTH)
    assert resp.status_code == 200
    body = resp.json()
    assert "sessions" in body
    assert body["sessions"] == []


def test_list_sessions_with_data(client, store):
    store.create_session(DEMO_USER)
    store.create_session(DEMO_USER)

    resp = client.get("/chat/sessions", headers=AUTH)
    assert resp.status_code == 200
    sessions = resp.json()["sessions"]
    assert len(sessions) == 2
    # Most recent first
    assert sessions[0]["last_active_at"] >= sessions[1]["last_active_at"]


# ── GET /chat/sessions/{session_id} ──────────────────────────────────────────


def test_get_session_detail(client, store):
    session = store.create_session(DEMO_USER)

    visible_turn = make_turn(session.session_id, kind="user_message", content="hello")
    hidden_turn = make_turn(session.session_id, kind="assistant_message", content="hi", hidden=True)
    store.append_turn(session.session_id, visible_turn)
    store.append_turn(session.session_id, hidden_turn)

    resp = client.get(f"/chat/sessions/{session.session_id}", headers=AUTH)
    assert resp.status_code == 200
    body = resp.json()
    assert body["session"]["session_id"] == session.session_id
    turns = body["turns"]
    assert len(turns) == 1
    assert turns[0]["content"] == "hello"


def test_get_session_not_found(client):
    resp = client.get("/chat/sessions/nonexistent", headers=AUTH)
    assert resp.status_code == 404


def test_get_session_wrong_user(client, store):
    other_session = store.create_session("u_other")
    resp = client.get(f"/chat/sessions/{other_session.session_id}", headers=AUTH)
    assert resp.status_code == 403


# ── POST /chat/sessions/{session_id}/turns ────────────────────────────────────


def test_create_turn_sse(client, store):
    session = store.create_session(DEMO_USER)

    async def mock_run_turn(session_id, inbound, storage, bunq_client, user_id, sse_emit):
        await sse_emit("delta", {"text": "Hello!"})
        await sse_emit("done", {"reason": "complete"})

    with patch("backend.routes.chat.run_turn", new=mock_run_turn):
        resp = client.post(
            f"/chat/sessions/{session.session_id}/turns",
            headers=AUTH,
            json={"type": "user_message", "content": "What's my gap?"},
        )

    assert resp.status_code == 200
    events = parse_sse_events(resp.text)
    event_names = [e["event"] for e in events]
    assert "delta" in event_names
    assert "done" in event_names


def test_create_turn_missing_session(client):
    resp = client.post(
        "/chat/sessions/does-not-exist/turns",
        headers=AUTH,
        json={"type": "user_message", "content": "hi"},
    )
    assert resp.status_code == 404


def test_create_turn_invalid_type(client, store):
    session = store.create_session(DEMO_USER)
    resp = client.post(
        f"/chat/sessions/{session.session_id}/turns",
        headers=AUTH,
        json={"type": "invalid"},
    )
    assert resp.status_code == 400


def test_create_turn_missing_content_for_user_message(client, store):
    session = store.create_session(DEMO_USER)
    resp = client.post(
        f"/chat/sessions/{session.session_id}/turns",
        headers=AUTH,
        json={"type": "user_message"},
    )
    assert resp.status_code == 400


def test_create_turn_missing_tool_use_id_for_approval(client, store):
    session = store.create_session(DEMO_USER)
    resp = client.post(
        f"/chat/sessions/{session.session_id}/turns",
        headers=AUTH,
        json={"type": "tool_approval", "decision": "approve"},
    )
    assert resp.status_code == 400


def test_list_sessions_requires_auth(client):
    resp = client.get("/chat/sessions")
    assert resp.status_code in (401, 422)
