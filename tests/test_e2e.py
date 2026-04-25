"""End-to-end integration tests for bunq Nest — Phase 10.

Exercises the full onboard → chat → approval flow with mocked Bedrock
and fixture bunq client. Uses TestClient (synchronous) against the real
FastAPI app with a fresh SQLite store per test.
"""

from __future__ import annotations

import json
import time
from types import SimpleNamespace
from unittest.mock import patch

import pytest
import ulid

from backend.deps import get_bunq_client, get_storage
from backend.main import app
from backend.models import Payslip, PendingTool, Profile, Target, Turn
from backend.storage.sqlite_store import SqliteStore, init_db


# ── SSE parsing ──────────────────────────────────────────────────────────────


def parse_sse_events(body: str) -> list[dict]:
    """Parse SSE response body into list of {event, data} dicts."""
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
    if current_event and current_data:
        events.append({"event": current_event, "data": json.loads(current_data)})
    return events


# ── MockStream and event helpers ─────────────────────────────────────────────


class MockStream:
    def __init__(self, events):
        self._events = events

    async def __aiter__(self):
        for e in self._events:
            yield e

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


def text_start(index=0):
    return SimpleNamespace(
        type="content_block_start",
        index=index,
        content_block=SimpleNamespace(type="text", text=""),
    )


def text_delta(text, index=0):
    return SimpleNamespace(
        type="content_block_delta",
        index=index,
        delta=SimpleNamespace(type="text_delta", text=text),
    )


def block_stop(index):
    return SimpleNamespace(type="content_block_stop", index=index)


def tool_start(index, tool_id, name):
    return SimpleNamespace(
        type="content_block_start",
        index=index,
        content_block=SimpleNamespace(type="tool_use", id=tool_id, name=name),
    )


def input_delta(index, partial_json):
    return SimpleNamespace(
        type="content_block_delta",
        index=index,
        delta=SimpleNamespace(type="input_json_delta", partial_json=partial_json),
    )


# ── Mock bunq client ────────────────────────────────────────────────────────


class MockBunqClient:
    def __init__(self):
        self.move_money_calls = []
        self.create_bucket_calls = []

    async def get_transactions(self, monetary_account_id=None):
        return {
            "monetary_account_id": "mock_ma_001",
            "balance_eur": 34000.0,
            "transactions": [
                {
                    "id": "t001",
                    "date": "2026-03-02",
                    "amount_eur": 1450.00,
                    "counterparty": "Savings transfer",
                    "description": "Transfer to House bucket",
                    "category": "savings",
                },
            ],
        }

    async def get_buckets(self):
        return [
            {
                "id": "bucket_house",
                "name": "House",
                "balance_eur": 34000.0,
                "goal_eur": 55000.0,
                "color": "teal",
            },
            {
                "id": "bucket_buffer",
                "name": "Buffer",
                "balance_eur": 3200.0,
                "goal_eur": 5000.0,
                "color": "green",
            },
        ]

    async def move_money(self, from_id, to_id, amount_eur):
        self.move_money_calls.append((from_id, to_id, amount_eur))
        return "exec_smoke_123"

    async def create_bucket(self, name, goal_eur):
        self.create_bucket_calls.append((name, goal_eur))
        return {"id": "bucket_new", "name": name, "balance_eur": 0, "goal_eur": goal_eur}


# ── Mock payslip extract result ──────────────────────────────────────────────


MOCK_PAYSLIP_RESULT = SimpleNamespace(
    gross_monthly_eur=4850.0,
    net_monthly_eur=3520.0,
    employer_name="Acme BV",
    pay_period="2026-03",
    confidence="high",
    source_s3_key="test/payslip.jpg",
)


# ── Fixtures ─────────────────────────────────────────────────────────────────


# Onboard routes use backend.auth.get_current_user_id → X-Dev-User-Id in dev mode
ONBOARD_AUTH = {"X-Dev-User-Id": "u_demo"}
# Chat routes use backend.deps.get_current_user_id → Bearer demo
CHAT_AUTH = {"Authorization": "Bearer demo"}


@pytest.fixture()
def bunq():
    return MockBunqClient()


@pytest.fixture()
def e2e_client(store, bunq):
    """TestClient wired with fresh store and mock bunq client.

    Note: chat routes use Depends(get_storage/get_bunq_client) so overrides work.
    The onboard route calls get_bunq_client() and get_storage() directly,
    so we patch those in do_onboard() as well.
    """
    app.dependency_overrides[get_storage] = lambda: store
    app.dependency_overrides[get_bunq_client] = lambda: bunq
    yield app
    app.dependency_overrides.clear()


def do_onboard(client, store, bunq, funda_data=None):
    """Helper: run onboard with mocked payslip + funda → return response.

    Patches the direct calls in onboard.py (not FastAPI Depends) plus the
    Bedrock/S3-dependent extract_and_persist and parse_funda.
    """
    if funda_data is None:
        funda_data = {
            "price_eur": 425000,
            "address": "Teststraat 1, Utrecht",
            "type": "Appartement",
            "size_m2": 85,
            "year_built": 2010,
        }

    with (
        patch(
            "backend.routes.onboard.payslip_module.extract_and_persist",
            return_value=MOCK_PAYSLIP_RESULT,
        ),
        patch(
            "backend.routes.onboard.funda_module.parse_funda",
            return_value=funda_data,
        ),
        patch(
            "backend.routes.onboard.get_bunq_client",
            return_value=bunq,
        ),
        patch(
            "backend.routes.onboard.get_storage",
            return_value=store,
        ),
    ):
        resp = client.post(
            "/onboard",
            headers=ONBOARD_AUTH,
            json={"s3_key": "test/payslip.jpg", "funda_url": "https://funda.nl/test"},
        )

    return resp


# ── Tests ────────────────────────────────────────────────────────────────────


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}


def test_full_onboard_flow(e2e_client, store, bunq):
    from fastapi.testclient import TestClient

    client = TestClient(e2e_client)
    resp = do_onboard(client, store, bunq)

    assert resp.status_code == 200
    body = resp.json()
    assert "session_id" in body
    assert "profile" in body

    profile = body["profile"]
    assert profile["payslip"]["gross_monthly_eur"] == 4850.0
    assert profile["payslip"]["net_monthly_eur"] == 3520.0
    assert profile["target"]["price_eur"] == 425000.0
    assert profile["target"]["address"] == "Teststraat 1, Utrecht"

    proj = profile["projection"]
    assert proj["savings_now_eur"] == 34000.0
    assert proj["deposit_target_eur"] > 0
    assert proj["gap_eur"] >= 0
    assert proj["months_to_goal"] >= 0
    assert len(proj["headroom_range_eur"]) == 2

    # Verify storage
    stored_profile = store.get_profile("u_demo")
    assert stored_profile is not None
    assert stored_profile.payslip.gross_monthly_eur == 4850.0

    session = store.get_latest_session("u_demo")
    assert session is not None
    assert session.session_id == body["session_id"]

    # Bootstrap hidden turn should exist
    turns = store.list_turns(session.session_id, include_hidden=True)
    hidden = [t for t in turns if t.hidden]
    assert len(hidden) == 1
    assert "profile bootstrapped" in hidden[0].content


def test_onboard_then_chat_text_response(e2e_client, store, bunq):
    from fastapi.testclient import TestClient

    client = TestClient(e2e_client)

    # Onboard
    onboard_resp = do_onboard(client, store, bunq)
    session_id = onboard_resp.json()["session_id"]

    # Chat — text-only response
    stream_events = [
        text_start(0),
        text_delta("Your savings gap is €21,000. ", 0),
        text_delta("At your current rate, about 15 months to go.", 0),
        block_stop(0),
    ]

    with patch("backend.agent.runner.stream_chat", return_value=MockStream(stream_events)):
        resp = client.post(
            f"/chat/sessions/{session_id}/turns",
            headers=CHAT_AUTH,
            json={"type": "user_message", "content": "How am I doing?"},
        )

    assert resp.status_code == 200
    events = parse_sse_events(resp.text)
    event_names = [e["event"] for e in events]

    assert "delta" in event_names
    assert "done" in event_names

    done = next(e for e in events if e["event"] == "done")
    assert done["data"]["reason"] == "complete"

    # Verify text was concatenated in deltas
    deltas = [e["data"]["text"] for e in events if e["event"] == "delta"]
    full_text = "".join(deltas)
    assert "savings gap" in full_text

    # Verify turns persisted
    turns = store.list_turns(session_id, include_hidden=False)
    kinds = [t.kind for t in turns]
    assert "user_message" in kinds
    assert "assistant_message" in kinds


def test_onboard_then_chat_read_tool_loop(e2e_client, store, bunq):
    from fastapi.testclient import TestClient

    client = TestClient(e2e_client)

    onboard_resp = do_onboard(client, store, bunq)
    session_id = onboard_resp.json()["session_id"]

    # First model call: text + tool use for get_bunq_buckets
    events1 = [
        text_start(0),
        text_delta("Let me check your buckets.", 0),
        block_stop(0),
        tool_start(1, "tu_read_01", "get_bunq_buckets"),
        input_delta(1, "{}"),
        block_stop(1),
    ]

    # Second model call: text-only response after seeing tool result
    events2 = [
        text_start(0),
        text_delta("You have €34,000 in your House bucket.", 0),
        block_stop(0),
    ]

    with patch(
        "backend.agent.runner.stream_chat",
        side_effect=[MockStream(events1), MockStream(events2)],
    ):
        resp = client.post(
            f"/chat/sessions/{session_id}/turns",
            headers=CHAT_AUTH,
            json={"type": "user_message", "content": "Check my savings buckets"},
        )

    assert resp.status_code == 200
    events = parse_sse_events(resp.text)
    event_names = [e["event"] for e in events]

    assert "delta" in event_names
    assert "tool_call" in event_names
    assert "tool_result" in event_names
    assert "done" in event_names

    done = next(e for e in events if e["event"] == "done")
    assert done["data"]["reason"] == "complete"

    # Verify tool_result event has bucket data
    tool_result = next(e for e in events if e["event"] == "tool_result")
    assert "bucket_house" in tool_result["data"].get("summary", "") or "House" in tool_result["data"].get("summary", "")


def test_onboard_then_write_proposal_and_approve(e2e_client, store, bunq):
    from fastapi.testclient import TestClient

    client = TestClient(e2e_client)

    onboard_resp = do_onboard(client, store, bunq)
    session_id = onboard_resp.json()["session_id"]

    # Model proposes a money move
    move_input = '{"from_bucket_id": "bucket_buffer", "to_bucket_id": "bucket_house", "amount_eur": 200, "reason": "Boost house savings"}'
    proposal_events = [
        text_start(0),
        text_delta("I suggest moving €200 from Buffer to House.", 0),
        block_stop(0),
        tool_start(1, "tu_write_01", "propose_move_money"),
        input_delta(1, move_input),
        block_stop(1),
    ]

    with patch("backend.agent.runner.stream_chat", return_value=MockStream(proposal_events)):
        resp = client.post(
            f"/chat/sessions/{session_id}/turns",
            headers=CHAT_AUTH,
            json={"type": "user_message", "content": "Move €200 from buffer to house fund"},
        )

    assert resp.status_code == 200
    events = parse_sse_events(resp.text)
    event_names = [e["event"] for e in events]

    assert "tool_proposal" in event_names
    assert "done" in event_names

    done = next(e for e in events if e["event"] == "done")
    assert done["data"]["reason"] == "awaiting_approval"

    proposal = next(e for e in events if e["event"] == "tool_proposal")
    tool_use_id = proposal["data"]["tool_use_id"]
    assert tool_use_id == "tu_write_01"

    # No bunq write should have happened yet
    assert bunq.move_money_calls == []

    # Pending tool should be in storage
    pending = store.get_pending_tool(session_id, tool_use_id)
    assert pending is not None
    assert pending.tool_name == "propose_move_money"

    # Now approve
    follow_up_events = [
        text_start(0),
        text_delta("Done! €200 moved to your House bucket.", 0),
        block_stop(0),
    ]

    with patch("backend.agent.runner.stream_chat", return_value=MockStream(follow_up_events)):
        resp = client.post(
            f"/chat/sessions/{session_id}/turns",
            headers=CHAT_AUTH,
            json={
                "type": "tool_approval",
                "tool_use_id": tool_use_id,
                "decision": "approve",
            },
        )

    assert resp.status_code == 200
    events = parse_sse_events(resp.text)
    event_names = [e["event"] for e in events]

    assert "done" in event_names
    done = next(e for e in events if e["event"] == "done")
    assert done["data"]["reason"] == "complete"

    # bunq write should have been called
    assert len(bunq.move_money_calls) == 1
    assert bunq.move_money_calls[0] == ("bucket_buffer", "bucket_house", 200)

    # Pending should be cleared
    assert store.get_pending_tool(session_id, tool_use_id) is None


def test_onboard_then_write_proposal_and_deny(e2e_client, store, bunq):
    from fastapi.testclient import TestClient

    client = TestClient(e2e_client)

    onboard_resp = do_onboard(client, store, bunq)
    session_id = onboard_resp.json()["session_id"]

    move_input = '{"from_bucket_id": "bucket_buffer", "to_bucket_id": "bucket_house", "amount_eur": 500, "reason": "Big boost"}'
    proposal_events = [
        text_start(0),
        text_delta("I suggest moving €500.", 0),
        block_stop(0),
        tool_start(1, "tu_write_02", "propose_move_money"),
        input_delta(1, move_input),
        block_stop(1),
    ]

    with patch("backend.agent.runner.stream_chat", return_value=MockStream(proposal_events)):
        resp = client.post(
            f"/chat/sessions/{session_id}/turns",
            headers=CHAT_AUTH,
            json={"type": "user_message", "content": "Move €500 from buffer to house"},
        )

    events = parse_sse_events(resp.text)
    proposal = next(e for e in events if e["event"] == "tool_proposal")
    tool_use_id = proposal["data"]["tool_use_id"]

    # Deny
    deny_follow_up = [
        text_start(0),
        text_delta("Understood, I won't move the money.", 0),
        block_stop(0),
    ]

    with patch("backend.agent.runner.stream_chat", return_value=MockStream(deny_follow_up)):
        resp = client.post(
            f"/chat/sessions/{session_id}/turns",
            headers=CHAT_AUTH,
            json={
                "type": "tool_approval",
                "tool_use_id": tool_use_id,
                "decision": "deny",
                "feedback": "Too much right now",
            },
        )

    assert resp.status_code == 200
    events = parse_sse_events(resp.text)
    event_names = [e["event"] for e in events]

    assert "done" in event_names

    # No bunq write
    assert bunq.move_money_calls == []

    # Pending cleared
    assert store.get_pending_tool(session_id, tool_use_id) is None

    # Declined result persisted
    turns = store.list_turns(session_id, include_hidden=True)
    result_turns = [t for t in turns if t.kind == "tool_result"]
    declined = [t for t in result_turns if t.result and t.result.get("declined_by_user")]
    assert len(declined) >= 1


def test_sessions_list_after_onboard(e2e_client, store, bunq):
    from fastapi.testclient import TestClient

    client = TestClient(e2e_client)

    # No sessions yet
    resp = client.get("/chat/sessions", headers=CHAT_AUTH)
    assert resp.json()["sessions"] == []

    # Onboard creates a session
    do_onboard(client, store, bunq)

    resp = client.get("/chat/sessions", headers=CHAT_AUTH)
    sessions = resp.json()["sessions"]
    assert len(sessions) == 1


def test_session_detail_hides_bootstrap_turn(e2e_client, store, bunq):
    from fastapi.testclient import TestClient

    client = TestClient(e2e_client)

    onboard_resp = do_onboard(client, store, bunq)
    session_id = onboard_resp.json()["session_id"]

    resp = client.get(f"/chat/sessions/{session_id}", headers=CHAT_AUTH)
    assert resp.status_code == 200
    body = resp.json()

    # Hidden bootstrap turn should NOT appear in the visible turn list
    turns = body["turns"]
    for t in turns:
        assert "profile bootstrapped" not in (t.get("content") or "")
