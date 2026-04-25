import time

from backend.models import BunqToken, PendingTool, Profile, Payslip, Turn


# ── Profiles ──────────────────────────────────────────────────────────────────


def test_profile_roundtrip(store):
    p = Profile(user_id="u1", email="a@b.com")
    store.upsert_profile(p)

    loaded = store.get_profile("u1")
    assert loaded is not None
    assert loaded.user_id == "u1"
    assert loaded.email == "a@b.com"


def test_profile_upsert_overwrites(store):
    store.upsert_profile(Profile(user_id="u1", email="old@b.com"))
    store.upsert_profile(Profile(user_id="u1", email="new@b.com"))

    loaded = store.get_profile("u1")
    assert loaded.email == "new@b.com"


def test_profile_missing_returns_none(store):
    assert store.get_profile("nonexistent") is None


def test_profile_with_payslip(store):
    p = Profile(
        user_id="u1",
        payslip=Payslip(
            gross_monthly_eur=5000.0,
            net_monthly_eur=3500.0,
            employer_name="Acme",
            confidence="high",
        ),
    )
    store.upsert_profile(p)
    loaded = store.get_profile("u1")
    assert loaded.payslip.gross_monthly_eur == 5000.0
    assert loaded.payslip.confidence == "high"


# ── Sessions ──────────────────────────────────────────────────────────────────


def test_create_and_get_session(store):
    session = store.create_session("u1")
    assert session.user_id == "u1"
    assert session.state == "active"

    latest = store.get_latest_session("u1")
    assert latest.session_id == session.session_id


def test_latest_session_returns_most_recent(store):
    store.create_session("u1")
    s2 = store.create_session("u1")

    latest = store.get_latest_session("u1")
    assert latest.session_id == s2.session_id


def test_no_session_returns_none(store):
    assert store.get_latest_session("nobody") is None


def test_touch_session_updates_timestamp(store):
    session = store.create_session("u1")
    original_ts = session.last_active_at

    # Small delay to ensure timestamp differs
    time.sleep(0.01)
    store.touch_session(session.session_id)

    updated = store.get_latest_session("u1")
    assert updated.last_active_at > original_ts


# ── Turns ─────────────────────────────────────────────────────────────────────


def test_append_and_list_turns(store):
    session = store.create_session("u1")
    now = int(time.time() * 1000)

    t1 = Turn(turn_id="t1", session_id=session.session_id, ts_ms=now, kind="user_message", content="hi")
    t2 = Turn(turn_id="t2", session_id=session.session_id, ts_ms=now + 1, kind="assistant_message", content="hello")
    store.append_turn(session.session_id, t1)
    store.append_turn(session.session_id, t2)

    turns = store.list_turns(session.session_id)
    assert len(turns) == 2
    assert turns[0].content == "hi"
    assert turns[1].content == "hello"


def test_hidden_turns_excluded_by_default(store):
    session = store.create_session("u1")
    now = int(time.time() * 1000)

    visible = Turn(turn_id="t1", session_id=session.session_id, ts_ms=now, kind="user_message", content="visible")
    hidden = Turn(turn_id="t2", session_id=session.session_id, ts_ms=now + 1, kind="tool_result", content="hidden", hidden=True)
    store.append_turn(session.session_id, visible)
    store.append_turn(session.session_id, hidden)

    assert len(store.list_turns(session.session_id)) == 1
    assert len(store.list_turns(session.session_id, include_hidden=True)) == 2


# ── Pending tools ─────────────────────────────────────────────────────────────


def test_pending_tool_lifecycle(store):
    session = store.create_session("u1")
    pending = PendingTool(
        tool_use_id="tu1",
        session_id=session.session_id,
        tool_name="propose_move_money",
        params={"amount": 100},
        summary="Move €100",
        rationale="Savings goal",
        risk_level="low",
        proposed_at=int(time.time() * 1000),
    )

    store.put_pending_tool(session.session_id, pending)
    loaded = store.get_pending_tool(session.session_id, "tu1")
    assert loaded is not None
    assert loaded.tool_name == "propose_move_money"

    store.clear_pending_tool(session.session_id, "tu1")
    assert store.get_pending_tool(session.session_id, "tu1") is None


def test_pending_tool_missing_returns_none(store):
    session = store.create_session("u1")
    assert store.get_pending_tool(session.session_id, "nonexistent") is None


# ── bunq tokens ───────────────────────────────────────────────────────────────


def test_bunq_token_roundtrip(store):
    token = BunqToken(
        user_id="u1",
        access_token="secret-access",
        refresh_token="secret-refresh",
        expires_at=int(time.time()) + 3600,
    )
    store.put_bunq_token("u1", token)

    loaded = store.get_bunq_token("u1")
    assert loaded is not None
    assert loaded.access_token == "secret-access"


def test_bunq_token_upsert(store):
    t1 = BunqToken(user_id="u1", access_token="old", expires_at=1000)
    t2 = BunqToken(user_id="u1", access_token="new", expires_at=2000)

    store.put_bunq_token("u1", t1)
    store.put_bunq_token("u1", t2)

    loaded = store.get_bunq_token("u1")
    assert loaded.access_token == "new"


def test_bunq_token_missing_returns_none(store):
    assert store.get_bunq_token("nobody") is None


def test_bunq_token_repr_redacts_secret():
    token = BunqToken(user_id="u1", access_token="super-secret", expires_at=999)
    r = repr(token)
    assert "super-secret" not in r
    assert "REDACTED" in r
