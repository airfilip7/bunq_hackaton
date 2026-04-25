"""Integration tests for RealBunqClient against the bunq sandbox API."""

from __future__ import annotations

import asyncio
from uuid import uuid4

import httpx
import pytest
import pytest_asyncio

from backend.bunq_client import RealBunqClient

SANDBOX_BASE_URL = "https://public-api.sandbox.bunq.com/v1"


@pytest_asyncio.fixture(scope="session")
async def sandbox_api_key() -> str:
    """Generate a fresh sandbox API key via the bunq sandbox endpoint."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{SANDBOX_BASE_URL}/sandbox-user-person",
            json={},
            headers={
                "Content-Type": "application/json",
                "X-Bunq-Client-Request-Id": str(uuid4()),
                "Cache-Control": "no-cache",
                "User-Agent": "bunq-nest-test",
                "X-Bunq-Geolocation": "0 0 0 0 000",
                "X-Bunq-Language": "en_US",
                "X-Bunq-Region": "en_US",
            },
        )
        resp.raise_for_status()
        data = resp.json()
        api_key = data["Response"][0]["ApiKey"]["api_key"]
        return api_key


@pytest_asyncio.fixture(scope="session")
async def bunq_client(sandbox_api_key: str) -> RealBunqClient:
    """Session-scoped RealBunqClient pointing at the bunq sandbox."""
    return RealBunqClient(
        api_key=sandbox_api_key,
        base_url=SANDBOX_BASE_URL,
        sandbox=True,
    )


@pytest.mark.sandbox
@pytest.mark.asyncio(loop_scope="session")
async def test_session_establishment(bunq_client: RealBunqClient) -> None:
    await bunq_client._ensure_session()
    assert isinstance(bunq_client._session_token, str) and bunq_client._session_token
    assert isinstance(bunq_client._bunq_user_id, int)


@pytest.mark.sandbox
@pytest.mark.asyncio(loop_scope="session")
async def test_get_transactions(bunq_client: RealBunqClient) -> None:
    result = await bunq_client.get_transactions()
    assert isinstance(result, dict)
    assert "monetary_account_id" in result
    assert "balance_eur" in result
    assert "transactions" in result
    assert isinstance(result["transactions"], list)
    assert isinstance(result["balance_eur"], (float, int))


@pytest.mark.sandbox
@pytest.mark.asyncio(loop_scope="session")
async def test_get_buckets(bunq_client: RealBunqClient) -> None:
    result = await bunq_client.get_buckets()
    assert isinstance(result, list)
    for bucket in result:
        assert "id" in bucket
        assert "name" in bucket
        assert "balance_eur" in bucket
        assert "goal_eur" in bucket
        assert "color" in bucket


@pytest.mark.sandbox
@pytest.mark.asyncio(loop_scope="session")
async def test_create_bucket(bunq_client: RealBunqClient) -> None:
    result = await bunq_client.create_bucket(name="Test Savings", goal_eur=1000.0)
    assert isinstance(result, dict)
    assert isinstance(result.get("id"), str) and result["id"]
    assert result["name"] == "Test Savings"
    assert result["balance_eur"] == 0.0
    assert result["goal_eur"] == 1000.0


async def _fund_account(bunq_client: RealBunqClient, account_id: str, amount_eur: float = 100.0) -> None:
    """Top up a sandbox account via the bunq 'sugar daddy' request-inquiry mechanism."""
    uid = bunq_client._bunq_user_id
    body = {
        "amount_inquired": {"value": str(amount_eur), "currency": "EUR"},
        "counterparty_alias": {"type": "EMAIL", "value": "sugardaddy@bunq.com"},
        "description": "Test funding",
        "allow_bunqme": False,
    }
    await bunq_client._post(f"/user/{uid}/monetary-account/{account_id}/request-inquiry", body)


@pytest.mark.sandbox
@pytest.mark.asyncio(loop_scope="session")
async def test_move_money(bunq_client: RealBunqClient) -> None:
    tx_info = await bunq_client.get_transactions()
    main_account_id = tx_info["monetary_account_id"]

    # Fund the main account; sugar daddy auto-accepts within ~2s
    await _fund_account(bunq_client, main_account_id, 50.0)
    await asyncio.sleep(3)

    target_bucket = await bunq_client.create_bucket(name="Move Target", goal_eur=500.0)

    ref = await bunq_client.move_money(
        from_id=main_account_id,
        to_id=target_bucket["id"],
        amount_eur=1.00,
    )
    assert isinstance(ref, str) and ref
    assert ref.startswith("exec_")


@pytest.mark.sandbox
@pytest.mark.asyncio(loop_scope="session")
async def test_session_reuse(bunq_client: RealBunqClient) -> None:
    token_before = bunq_client._session_token
    await bunq_client.get_buckets()
    assert bunq_client._session_token == token_before
