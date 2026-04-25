"""Tests for Phase 8 — backend/agent/system_prompt.py and backend/agent/tools.py."""

import json
import pytest

from backend.agent.system_prompt import build_system_prompt
from backend.agent.tools import (
    KNOWN_TOOLS,
    READ_TOOLS,
    TOOL_SCHEMAS,
    ToolContext,
    _truncate_result,
    execute_read_tool,
    is_read_only,
)
from backend.models import Payslip, Profile, Projection, Target


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture()
def full_profile(store) -> Profile:
    profile = Profile(
        user_id="u_test",
        payslip=Payslip(
            gross_monthly_eur=4850.0,
            net_monthly_eur=3520.0,
            employer_name="Acme BV",
            confidence="high",
        ),
        target=Target(
            funda_url="https://funda.nl/test",
            price_eur=425_000.0,
            address="Utrecht",
        ),
        projection=Projection(
            savings_now_eur=34_000.0,
            deposit_target_eur=55_000.0,
            gap_eur=21_000.0,
            monthly_savings_eur=1450.0,
            months_to_goal=15,
            headroom_range_eur=(268_200, 314_280),
            computed_at=1_000_000,
        ),
    )
    store.upsert_profile(profile)
    return profile


# ── Part 1: build_system_prompt ───────────────────────────────────────────────


def test_system_prompt_includes_coaching_agent(store, full_profile):
    from backend.prompts import COACHING_AGENT
    prompt = build_system_prompt("u_test", store)
    assert COACHING_AGENT in prompt


def test_system_prompt_includes_disclaimer(store, full_profile):
    from backend.prompts import DISCLAIMER
    prompt = build_system_prompt("u_test", store)
    assert DISCLAIMER in prompt


def test_system_prompt_includes_profile_data(store, full_profile):
    prompt = build_system_prompt("u_test", store)
    assert "4,850.00" in prompt
    assert "425,000.00" in prompt
    assert "34,000.00" in prompt
    assert "21,000.00" in prompt
    assert "Acme BV" in prompt
    assert "Utrecht" in prompt


def test_system_prompt_no_profile(store):
    prompt = build_system_prompt("u_nobody", store)

    from backend.prompts import COACHING_AGENT, DISCLAIMER
    assert COACHING_AGENT in prompt
    assert DISCLAIMER in prompt
    assert "propose_move_money" in prompt
    assert "User Profile Snapshot" not in prompt


def test_system_prompt_includes_nibud_norms(store, full_profile):
    prompt = build_system_prompt("u_test", store)
    assert "Nibud" in prompt
    assert "5" in prompt
    assert "8%" in prompt


def test_system_prompt_includes_tool_reminder(store, full_profile):
    prompt = build_system_prompt("u_test", store)
    assert "propose_move_money" in prompt
    assert "propose_create_bucket" in prompt
    assert "get_bunq_transactions" in prompt


def test_system_prompt_partial_profile(store):
    profile = Profile(
        user_id="u_partial",
        payslip=Payslip(
            gross_monthly_eur=4850.0,
            net_monthly_eur=3520.0,
            employer_name="Acme BV",
            confidence="high",
        ),
    )
    store.upsert_profile(profile)

    prompt = build_system_prompt("u_partial", store)
    assert "4,850.00" in prompt
    assert "Acme BV" in prompt
    assert "Target Property" not in prompt
    assert "Current Projection" not in prompt


# ── Part 2: TOOL_SCHEMAS, is_read_only, execute_read_tool ────────────────────


def test_tool_schemas_count():
    assert len(TOOL_SCHEMAS) == 6


def test_tool_schemas_names():
    names = {t["name"] for t in TOOL_SCHEMAS}
    assert names == {
        "get_bunq_transactions",
        "get_bunq_buckets",
        "get_funda_property",
        "compute_projection",
        "propose_move_money",
        "propose_create_bucket",
    }


def test_known_tools_matches_schemas():
    assert KNOWN_TOOLS == {t["name"] for t in TOOL_SCHEMAS}


def test_is_read_only_read_tools():
    for name in READ_TOOLS:
        assert is_read_only(name) is True


def test_is_read_only_write_tools():
    assert is_read_only("propose_move_money") is False
    assert is_read_only("propose_create_bucket") is False


def test_is_read_only_unknown():
    assert is_read_only("some_random_tool") is True


# ── Mock bunq clients ─────────────────────────────────────────────────────────


class MockBunqClientTransactions:
    async def get_transactions(self, monetary_account_id=None):
        return {
            "transactions": [
                {"id": "t1", "date": "2026-04-01", "amount_eur": 100}
            ],
            "balance_eur": 100,
        }

    async def get_buckets(self):
        return []


class MockBunqClientBuckets:
    async def get_transactions(self, monetary_account_id=None):
        return {"transactions": [], "balance_eur": 0}

    async def get_buckets(self):
        return [{"id": "b1", "name": "House", "balance_eur": 34_000.0, "goal_eur": 55_000.0}]


class MockBunqClientProjection:
    async def get_transactions(self, monetary_account_id=None):
        return {
            "transactions": [
                {"id": "t1", "date": "2026-04-01", "amount_eur": 1450.0, "category": "savings"},
                {"id": "t2", "date": "2026-03-01", "amount_eur": 1450.0, "category": "savings"},
                {"id": "t3", "date": "2026-02-01", "amount_eur": 1450.0, "category": "savings"},
            ],
            "balance_eur": 34_000,
        }

    async def get_buckets(self):
        return [{"id": "b1", "name": "House", "balance_eur": 34_000.0, "goal_eur": 55_000.0}]


# ── async tool dispatch tests ─────────────────────────────────────────────────


async def test_execute_read_tool_transactions(store):
    ctx = ToolContext(
        bunq_client=MockBunqClientTransactions(),
        storage=store,
        user_id="u_test",
    )
    result = await execute_read_tool("get_bunq_transactions", {"window_days": 30}, ctx)
    assert "transactions" in result
    assert "total_count" in result
    assert "window_days" in result


async def test_execute_read_tool_buckets(store):
    ctx = ToolContext(
        bunq_client=MockBunqClientBuckets(),
        storage=store,
        user_id="u_test",
    )
    result = await execute_read_tool("get_bunq_buckets", {}, ctx)
    assert result == {"buckets": [{"id": "b1", "name": "House", "balance_eur": 34_000.0, "goal_eur": 55_000.0}]}


async def test_execute_read_tool_compute_projection(store):
    profile = Profile(
        user_id="u_proj",
        payslip=Payslip(gross_monthly_eur=4850.0, net_monthly_eur=3520.0, confidence="high"),
        target=Target(funda_url="https://funda.nl/test", price_eur=425_000.0),
    )
    store.upsert_profile(profile)

    ctx = ToolContext(
        bunq_client=MockBunqClientProjection(),
        storage=store,
        user_id="u_proj",
    )
    result = await execute_read_tool("compute_projection", {}, ctx)
    assert "savings_now_eur" in result
    assert "gap_eur" in result
    assert "months_to_goal" in result


async def test_execute_read_tool_unknown(store):
    ctx = ToolContext(
        bunq_client=MockBunqClientTransactions(),
        storage=store,
        user_id="u_test",
    )
    with pytest.raises(AssertionError):
        await execute_read_tool("nonexistent", {}, ctx)


async def test_execute_read_tool_write_tool_rejected(store):
    ctx = ToolContext(
        bunq_client=MockBunqClientTransactions(),
        storage=store,
        user_id="u_test",
    )
    with pytest.raises(AssertionError):
        await execute_read_tool("propose_move_money", {}, ctx)


# ── _truncate_result ──────────────────────────────────────────────────────────


def test_truncate_result_small_fits():
    data = {"transactions": [{"id": "t1", "amount_eur": 10}], "total_count": 1}
    result = _truncate_result(data)
    assert result == data


def test_truncate_result_large_truncated():
    transactions = [
        {"id": f"t{i}", "date": f"2026-01-{i % 28 + 1:02d}", "amount_eur": float(i), "description": "x" * 20}
        for i in range(100)
    ]
    data = {"transactions": transactions, "total_count": 100}

    result = _truncate_result(data)
    assert len(json.dumps(result)) <= 2000
    # Oldest entries (front of list) should have been dropped
    remaining_ids = [t["id"] for t in result["transactions"]]
    if remaining_ids:
        assert "t0" not in remaining_ids
