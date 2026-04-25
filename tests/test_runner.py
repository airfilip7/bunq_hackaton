"""Tests for backend/agent/runner.py — Phase 8 Task 3."""

from __future__ import annotations

import time
from types import SimpleNamespace
from unittest.mock import patch

import ulid

from backend.agent.runner import execute_write_tool, run_turn, turns_to_messages
from backend.models import Payslip, PendingTool, Profile, Target, Turn


# ── MockStream ────────────────────────────────────────────────────────────────


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


# ── Event helpers ─────────────────────────────────────────────────────────────


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


# ── MockBunqClient ────────────────────────────────────────────────────────────


class MockBunqClient:
    def __init__(self):
        self.move_money_calls = []
        self.create_bucket_calls = []

    async def get_transactions(self, monetary_account_id=None):
        return {"transactions": [], "balance_eur": 0}

    async def get_buckets(self):
        return [{"id": "b1", "name": "House", "balance_eur": 34000, "goal_eur": 55000}]

    async def move_money(self, from_id, to_id, amount_eur):
        self.move_money_calls.append((from_id, to_id, amount_eur))
        return "exec_test123"

    async def create_bucket(self, name, goal_eur):
        self.create_bucket_calls.append((name, goal_eur))
        return {"id": "bucket_new", "name": name, "balance_eur": 0, "goal_eur": goal_eur}


# ── SseCollector ──────────────────────────────────────────────────────────────


class SseCollector:
    def __init__(self):
        self.events: list[tuple[str, dict]] = []

    async def __call__(self, event: str, data: dict):
        self.events.append((event, data))


# ── Helpers ───────────────────────────────────────────────────────────────────


def make_turn(session_id: str, **kwargs) -> Turn:
    return Turn(
        turn_id=str(ulid.ULID()),
        session_id=session_id,
        ts_ms=int(time.time() * 1000),
        **kwargs,
    )


def make_profile(user_id: str = "u_test") -> Profile:
    return Profile(
        user_id=user_id,
        payslip=Payslip(gross_monthly_eur=4850, net_monthly_eur=3520, confidence="high"),
        target=Target(funda_url="https://funda.nl/test", price_eur=425000),
    )


# ── turns_to_messages ─────────────────────────────────────────────────────────


def test_turns_to_messages_basic():
    sid = "sess_1"
    turns = [
        make_turn(sid, kind="user_message", content="Hello"),
        make_turn(sid, kind="assistant_message", content="Hi there"),
        make_turn(
            sid,
            kind="tool_result",
            tool_use_id="tu_1",
            tool_name="get_bunq_buckets",
            ok=True,
            result={"buckets": []},
        ),
    ]
    messages = turns_to_messages(turns)

    # user_message → role=user, assistant_message → role=assistant
    # tool_result → role=user (merged with nothing or separate)
    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "assistant"
    # tool_result becomes a user message
    assert any(m["role"] == "user" for m in messages[1:])

    # Check assistant content is a list with a text block
    asst_content = messages[1]["content"]
    assert isinstance(asst_content, list)
    assert any(b.get("type") == "text" for b in asst_content)


def test_turns_to_messages_skips_approval():
    sid = "sess_2"
    turns = [
        make_turn(sid, kind="user_message", content="Move money"),
        make_turn(
            sid,
            kind="tool_approval",
            tool_use_id="tu_1",
            decision="approve",
        ),
        make_turn(sid, kind="assistant_message", content="Done"),
    ]
    messages = turns_to_messages(turns)

    # tool_approval must be skipped, so only 2 messages
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "assistant"


def test_turns_to_messages_merges_consecutive_roles():
    sid = "sess_3"
    # user_message followed immediately by tool_result (both map to role=user)
    turns = [
        make_turn(sid, kind="user_message", content="Hello"),
        make_turn(
            sid,
            kind="tool_result",
            tool_use_id="tu_1",
            tool_name="get_bunq_buckets",
            ok=True,
            result={"buckets": []},
        ),
    ]
    messages = turns_to_messages(turns)

    # Both are user-role → should be merged into one message
    assert len(messages) == 1
    assert messages[0]["role"] == "user"
    # Merged content is a list with both entries
    content = messages[0]["content"]
    assert isinstance(content, list)
    assert len(content) == 2


# ── run_turn: text response ───────────────────────────────────────────────────


async def test_run_turn_text_response(store):
    store.upsert_profile(make_profile())
    session = store.create_session("u_test")

    events = [
        text_start(0),
        text_delta("Hello!", 0),
        block_stop(0),
    ]

    sse = SseCollector()

    with patch("backend.agent.runner.stream_chat", return_value=MockStream(events)):
        await run_turn(
            session_id=session.session_id,
            inbound={"type": "user_message", "content": "What is my gap?"},
            storage=store,
            bunq_client=MockBunqClient(),
            user_id="u_test",
            sse_emit=sse,
        )

    event_types = [e[0] for e in sse.events]
    assert "delta" in event_types
    assert "done" in event_types
    done_event = next(e for e in sse.events if e[0] == "done")
    assert done_event[1]["reason"] == "complete"

    turns = store.list_turns(session.session_id, include_hidden=True)
    kinds = [t.kind for t in turns]
    assert "user_message" in kinds
    assert "assistant_message" in kinds


# ── run_turn: read tool loop ──────────────────────────────────────────────────


async def test_run_turn_read_tool_loop(store):
    store.upsert_profile(make_profile())
    session = store.create_session("u_test")

    # First stream: text + tool use for get_bunq_buckets
    events1 = [
        text_start(0),
        text_delta("Let me check your buckets.", 0),
        block_stop(0),
        tool_start(1, "tu_abc", "get_bunq_buckets"),
        input_delta(1, "{}"),
        block_stop(1),
    ]

    # Second stream: just text
    events2 = [
        text_start(0),
        text_delta("You have €34k in your House bucket.", 0),
        block_stop(0),
    ]

    sse = SseCollector()

    with patch(
        "backend.agent.runner.stream_chat",
        side_effect=[MockStream(events1), MockStream(events2)],
    ):
        await run_turn(
            session_id=session.session_id,
            inbound={"type": "user_message", "content": "Check my buckets"},
            storage=store,
            bunq_client=MockBunqClient(),
            user_id="u_test",
            sse_emit=sse,
        )

    event_types = [e[0] for e in sse.events]
    assert "tool_call" in event_types
    assert "tool_result" in event_types
    assert "delta" in event_types
    done_event = next(e for e in sse.events if e[0] == "done")
    assert done_event[1]["reason"] == "complete"


# ── run_turn: write tool proposal ─────────────────────────────────────────────


async def test_run_turn_write_tool_proposal(store):
    store.upsert_profile(make_profile())
    session = store.create_session("u_test")

    move_input = '{"from_bucket_id": "b1", "to_bucket_id": "b2", "amount_eur": 200, "reason": "Save more"}'
    events = [
        text_start(0),
        text_delta("I suggest moving some money.", 0),
        block_stop(0),
        tool_start(1, "tu_write1", "propose_move_money"),
        input_delta(1, move_input),
        block_stop(1),
    ]

    bunq = MockBunqClient()
    sse = SseCollector()

    with patch("backend.agent.runner.stream_chat", return_value=MockStream(events)):
        await run_turn(
            session_id=session.session_id,
            inbound={"type": "user_message", "content": "Move money to house fund"},
            storage=store,
            bunq_client=bunq,
            user_id="u_test",
            sse_emit=sse,
        )

    event_types = [e[0] for e in sse.events]
    assert "tool_proposal" in event_types
    done_event = next(e for e in sse.events if e[0] == "done")
    assert done_event[1]["reason"] == "awaiting_approval"

    # No actual bunq write should have happened
    assert bunq.move_money_calls == []

    # Pending tool should be in storage
    pending = store.get_pending_tool(session.session_id, "tu_write1")
    assert pending is not None
    assert pending.tool_name == "propose_move_money"


# ── run_turn: approval — approve ──────────────────────────────────────────────


async def test_run_turn_approval_approve(store):
    store.upsert_profile(make_profile())
    session = store.create_session("u_test")

    # Pre-populate a pending tool
    pending = PendingTool(
        tool_use_id="tu_pending",
        session_id=session.session_id,
        tool_name="propose_move_money",
        params={"from_bucket_id": "b1", "to_bucket_id": "b2", "amount_eur": 200, "reason": "House"},
        summary="Move €200 to House",
        rationale="House",
        risk_level="low",
        proposed_at=int(time.time() * 1000),
    )
    store.put_pending_tool(session.session_id, pending)

    # Also store an assistant turn that proposed it
    store.append_turn(
        session.session_id,
        make_turn(
            session.session_id,
            kind="assistant_message",
            content="I suggest moving money.",
            tool_uses=[{"id": "tu_pending", "name": "propose_move_money", "input": pending.params}],
        ),
    )

    # Mock model follow-up after approval
    follow_up_events = [
        text_start(0),
        text_delta("Done! Money moved.", 0),
        block_stop(0),
    ]

    bunq = MockBunqClient()
    sse = SseCollector()

    with patch("backend.agent.runner.stream_chat", return_value=MockStream(follow_up_events)):
        await run_turn(
            session_id=session.session_id,
            inbound={
                "type": "tool_approval",
                "tool_use_id": "tu_pending",
                "decision": "approve",
            },
            storage=store,
            bunq_client=bunq,
            user_id="u_test",
            sse_emit=sse,
        )

    # bunq write should have been called
    assert len(bunq.move_money_calls) == 1
    assert bunq.move_money_calls[0] == ("b1", "b2", 200)

    # Pending cleared
    assert store.get_pending_tool(session.session_id, "tu_pending") is None

    # tool_result Turn persisted
    turns = store.list_turns(session.session_id, include_hidden=True)
    kinds = [t.kind for t in turns]
    assert "tool_result" in kinds

    # Model follow-up ran
    event_types = [e[0] for e in sse.events]
    assert "done" in event_types


# ── run_turn: approval — deny ─────────────────────────────────────────────────


async def test_run_turn_approval_deny(store):
    store.upsert_profile(make_profile())
    session = store.create_session("u_test")

    pending = PendingTool(
        tool_use_id="tu_deny",
        session_id=session.session_id,
        tool_name="propose_move_money",
        params={"from_bucket_id": "b1", "to_bucket_id": "b2", "amount_eur": 500, "reason": "House"},
        summary="Move €500",
        rationale="House",
        risk_level="low",
        proposed_at=int(time.time() * 1000),
    )
    store.put_pending_tool(session.session_id, pending)

    store.append_turn(
        session.session_id,
        make_turn(
            session.session_id,
            kind="assistant_message",
            content="Propose move.",
            tool_uses=[{"id": "tu_deny", "name": "propose_move_money", "input": pending.params}],
        ),
    )

    follow_up_events = [
        text_start(0),
        text_delta("Understood, cancelled.", 0),
        block_stop(0),
    ]

    bunq = MockBunqClient()
    sse = SseCollector()

    with patch("backend.agent.runner.stream_chat", return_value=MockStream(follow_up_events)):
        await run_turn(
            session_id=session.session_id,
            inbound={
                "type": "tool_approval",
                "tool_use_id": "tu_deny",
                "decision": "deny",
                "feedback": "Not now",
            },
            storage=store,
            bunq_client=bunq,
            user_id="u_test",
            sse_emit=sse,
        )

    # No bunq write
    assert bunq.move_money_calls == []

    # Pending cleared
    assert store.get_pending_tool(session.session_id, "tu_deny") is None

    # tool_result Turn with declined result
    turns = store.list_turns(session.session_id, include_hidden=True)
    result_turns = [t for t in turns if t.kind == "tool_result"]
    assert len(result_turns) >= 1
    assert result_turns[-1].result.get("declined_by_user") is True


# ── run_turn: approval — missing pending ──────────────────────────────────────


async def test_run_turn_approval_missing(store):
    store.upsert_profile(make_profile())
    session = store.create_session("u_test")

    sse = SseCollector()

    # No pending tool stored — should emit error
    with patch("backend.agent.runner.stream_chat"):
        await run_turn(
            session_id=session.session_id,
            inbound={
                "type": "tool_approval",
                "tool_use_id": "tu_nonexistent",
                "decision": "approve",
            },
            storage=store,
            bunq_client=MockBunqClient(),
            user_id="u_test",
            sse_emit=sse,
        )

    event_types = [e[0] for e in sse.events]
    assert "error" in event_types


# ── run_turn: stream error ────────────────────────────────────────────────────


async def test_run_turn_stream_error(store):
    store.upsert_profile(make_profile())
    session = store.create_session("u_test")

    # Stream yields some text then raises
    async def _bad_stream_iter(self):
        yield text_delta("Partial text", 0)
        raise RuntimeError("Bedrock timeout")

    class ErrorStream:
        async def __aiter__(self):
            yield text_start(0)
            yield text_delta("Partial text", 0)
            raise RuntimeError("Bedrock timeout")

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

    sse = SseCollector()

    with patch("backend.agent.runner.stream_chat", return_value=ErrorStream()):
        await run_turn(
            session_id=session.session_id,
            inbound={"type": "user_message", "content": "Hi"},
            storage=store,
            bunq_client=MockBunqClient(),
            user_id="u_test",
            sse_emit=sse,
        )

    event_types = [e[0] for e in sse.events]
    assert "error" in event_types

    # Buffered text should have been persisted as a Turn
    turns = store.list_turns(session.session_id, include_hidden=True)
    asst_turns = [t for t in turns if t.kind == "assistant_message"]
    assert len(asst_turns) >= 1
    assert asst_turns[-1].content == "Partial text"


# ── execute_write_tool ────────────────────────────────────────────────────────


async def test_execute_write_tool_move_money():
    bunq = MockBunqClient()
    result = await execute_write_tool(
        "propose_move_money",
        {"from_bucket_id": "b1", "to_bucket_id": "b2", "amount_eur": 100},
        bunq,
    )
    assert result["ok"] is True
    assert result["execution_ref"] == "exec_test123"
    assert bunq.move_money_calls == [("b1", "b2", 100)]


async def test_execute_write_tool_create_bucket():
    bunq = MockBunqClient()
    result = await execute_write_tool(
        "propose_create_bucket",
        {"name": "Emergency", "target_eur": 5000},
        bunq,
    )
    assert result["ok"] is True
    assert result["bucket"]["name"] == "Emergency"
    assert bunq.create_bucket_calls == [("Emergency", 5000)]


async def test_execute_write_tool_unknown():
    bunq = MockBunqClient()
    result = await execute_write_tool("unknown_tool", {}, bunq)
    assert result["ok"] is False
    assert "Unknown write tool" in result["error"]


# ── Phase 9: approval override validation ─────────────────────────────────────


def _make_move_money_pending(session_id: str) -> PendingTool:
    return PendingTool(
        tool_use_id="tu_phase9",
        session_id=session_id,
        tool_name="propose_move_money",
        params={"from_bucket_id": "b1", "to_bucket_id": "b2", "amount_eur": 200, "reason": "House"},
        summary="Move €200 to House",
        rationale="Accelerate savings",
        risk_level="low",
        proposed_at=int(time.time() * 1000),
    )


def _store_pending_with_assistant_turn(store, session_id: str, pending: PendingTool) -> None:
    store.put_pending_tool(session_id, pending)
    store.append_turn(
        session_id,
        make_turn(
            session_id,
            kind="assistant_message",
            content="I suggest moving money.",
            tool_uses=[{"id": pending.tool_use_id, "name": pending.tool_name, "input": pending.params}],
        ),
    )


async def test_run_turn_approval_with_valid_overrides(store):
    store.upsert_profile(make_profile())
    session = store.create_session("u_test")
    pending = _make_move_money_pending(session.session_id)
    _store_pending_with_assistant_turn(store, session.session_id, pending)

    follow_up_events = [
        text_start(0),
        text_delta("Done! €300 moved.", 0),
        block_stop(0),
    ]

    bunq = MockBunqClient()
    sse = SseCollector()

    with patch("backend.agent.runner.stream_chat", return_value=MockStream(follow_up_events)):
        await run_turn(
            session_id=session.session_id,
            inbound={
                "type": "tool_approval",
                "tool_use_id": "tu_phase9",
                "decision": "approve",
                "overrides": {"amount_eur": 300},
            },
            storage=store,
            bunq_client=bunq,
            user_id="u_test",
            sse_emit=sse,
        )

    # bunq called with overridden amount
    assert len(bunq.move_money_calls) == 1
    assert bunq.move_money_calls[0] == ("b1", "b2", 300)

    # Pending cleared
    assert store.get_pending_tool(session.session_id, "tu_phase9") is None


async def test_run_turn_approval_with_invalid_override_key(store):
    store.upsert_profile(make_profile())
    session = store.create_session("u_test")
    pending = _make_move_money_pending(session.session_id)
    _store_pending_with_assistant_turn(store, session.session_id, pending)

    bunq = MockBunqClient()
    sse = SseCollector()

    with patch("backend.agent.runner.stream_chat"):
        await run_turn(
            session_id=session.session_id,
            inbound={
                "type": "tool_approval",
                "tool_use_id": "tu_phase9",
                "decision": "approve",
                "overrides": {"hacker_field": "pwned"},
            },
            storage=store,
            bunq_client=bunq,
            user_id="u_test",
            sse_emit=sse,
        )

    event_types = [e[0] for e in sse.events]
    assert "error" in event_types

    # Pending cleared even on validation failure
    assert store.get_pending_tool(session.session_id, "tu_phase9") is None

    # bunq NOT called
    assert bunq.move_money_calls == []


async def test_run_turn_approval_with_invalid_override_type(store):
    store.upsert_profile(make_profile())
    session = store.create_session("u_test")
    pending = _make_move_money_pending(session.session_id)
    _store_pending_with_assistant_turn(store, session.session_id, pending)

    bunq = MockBunqClient()
    sse = SseCollector()

    with patch("backend.agent.runner.stream_chat"):
        await run_turn(
            session_id=session.session_id,
            inbound={
                "type": "tool_approval",
                "tool_use_id": "tu_phase9",
                "decision": "approve",
                "overrides": {"amount_eur": "not a number"},
            },
            storage=store,
            bunq_client=bunq,
            user_id="u_test",
            sse_emit=sse,
        )

    event_types = [e[0] for e in sse.events]
    assert "error" in event_types
    assert store.get_pending_tool(session.session_id, "tu_phase9") is None
    assert bunq.move_money_calls == []


async def test_run_turn_approval_with_negative_amount_override(store):
    store.upsert_profile(make_profile())
    session = store.create_session("u_test")
    pending = _make_move_money_pending(session.session_id)
    _store_pending_with_assistant_turn(store, session.session_id, pending)

    bunq = MockBunqClient()
    sse = SseCollector()

    with patch("backend.agent.runner.stream_chat"):
        await run_turn(
            session_id=session.session_id,
            inbound={
                "type": "tool_approval",
                "tool_use_id": "tu_phase9",
                "decision": "approve",
                "overrides": {"amount_eur": -50},
            },
            storage=store,
            bunq_client=bunq,
            user_id="u_test",
            sse_emit=sse,
        )

    event_types = [e[0] for e in sse.events]
    assert "error" in event_types
    assert store.get_pending_tool(session.session_id, "tu_phase9") is None
    assert bunq.move_money_calls == []


async def test_tool_proposal_includes_rationale_and_risk(store):
    store.upsert_profile(make_profile())
    session = store.create_session("u_test")

    move_input = '{"from_bucket_id": "b1", "to_bucket_id": "b2", "amount_eur": 200, "reason": "Save more"}'
    events = [
        text_start(0),
        text_delta("I suggest moving some money.", 0),
        block_stop(0),
        tool_start(1, "tu_rationale1", "propose_move_money"),
        input_delta(1, move_input),
        block_stop(1),
    ]

    sse = SseCollector()

    with patch("backend.agent.runner.stream_chat", return_value=MockStream(events)):
        await run_turn(
            session_id=session.session_id,
            inbound={"type": "user_message", "content": "Move money to house fund"},
            storage=store,
            bunq_client=MockBunqClient(),
            user_id="u_test",
            sse_emit=sse,
        )

    proposal_events = [e for e in sse.events if e[0] == "tool_proposal"]
    assert len(proposal_events) == 1
    proposal_data = proposal_events[0][1]
    assert "rationale" in proposal_data
    assert "risk_level" in proposal_data


class ErrorBunqClient(MockBunqClient):
    async def move_money(self, from_id, to_id, amount_eur):
        raise ValueError("Insufficient balance in b1: 100.00 < 200.00")


async def test_run_turn_approval_bunq_error(store):
    store.upsert_profile(make_profile())
    session = store.create_session("u_test")
    pending = _make_move_money_pending(session.session_id)
    _store_pending_with_assistant_turn(store, session.session_id, pending)

    follow_up_events = [
        text_start(0),
        text_delta("Sorry, the transfer failed.", 0),
        block_stop(0),
    ]

    bunq = ErrorBunqClient()
    sse = SseCollector()

    with patch("backend.agent.runner.stream_chat", return_value=MockStream(follow_up_events)):
        await run_turn(
            session_id=session.session_id,
            inbound={
                "type": "tool_approval",
                "tool_use_id": "tu_phase9",
                "decision": "approve",
            },
            storage=store,
            bunq_client=bunq,
            user_id="u_test",
            sse_emit=sse,
        )

    # tool_result SSE event has ok: False
    tool_result_events = [e for e in sse.events if e[0] == "tool_result"]
    assert len(tool_result_events) >= 1
    assert tool_result_events[0][1]["ok"] is False

    # Pending cleared
    assert store.get_pending_tool(session.session_id, "tu_phase9") is None

    # tool_result Turn persisted with ok=False
    turns = store.list_turns(session.session_id, include_hidden=True)
    result_turns = [t for t in turns if t.kind == "tool_result"]
    assert len(result_turns) >= 1
    assert result_turns[-1].ok is False

    # Model follow-up ran (done event exists)
    event_types = [e[0] for e in sse.events]
    assert "done" in event_types


async def test_run_turn_approval_create_bucket(store):
    store.upsert_profile(make_profile())
    session = store.create_session("u_test")

    pending = PendingTool(
        tool_use_id="tu_bucket1",
        session_id=session.session_id,
        tool_name="propose_create_bucket",
        params={"name": "Holiday", "target_eur": 2000, "reason": "Vacation savings"},
        summary="Create Holiday bucket",
        rationale="Vacation savings",
        risk_level="low",
        proposed_at=int(time.time() * 1000),
    )
    store.put_pending_tool(session.session_id, pending)
    store.append_turn(
        session.session_id,
        make_turn(
            session.session_id,
            kind="assistant_message",
            content="Let me create a Holiday bucket.",
            tool_uses=[{"id": "tu_bucket1", "name": "propose_create_bucket", "input": pending.params}],
        ),
    )

    follow_up_events = [
        text_start(0),
        text_delta("Holiday bucket created!", 0),
        block_stop(0),
    ]

    bunq = MockBunqClient()
    sse = SseCollector()

    with patch("backend.agent.runner.stream_chat", return_value=MockStream(follow_up_events)):
        await run_turn(
            session_id=session.session_id,
            inbound={
                "type": "tool_approval",
                "tool_use_id": "tu_bucket1",
                "decision": "approve",
            },
            storage=store,
            bunq_client=bunq,
            user_id="u_test",
            sse_emit=sse,
        )

    assert bunq.create_bucket_calls == [("Holiday", 2000)]
    assert store.get_pending_tool(session.session_id, "tu_bucket1") is None
