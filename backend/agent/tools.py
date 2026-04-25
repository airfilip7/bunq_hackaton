"""Tool schemas, classification, and read-tool dispatch for the bunq Nest chat agent."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any

from backend.projection import compute_projection as _compute_projection

TOOL_SCHEMAS = [
    {
        "name": "get_bunq_transactions",
        "description": "Recent transactions for the user's monetary accounts. Read-only.",
        "input_schema": {
            "type": "object",
            "properties": {
                "window_days": {"type": "integer", "minimum": 1, "maximum": 365}
            },
            "required": ["window_days"],
        },
    },
    {
        "name": "get_bunq_buckets",
        "description": "Current Savings buckets and balances. Read-only.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_funda_property",
        "description": "Re-fetch the user's target Funda listing.",
        "input_schema": {
            "type": "object",
            "properties": {"url": {"type": "string"}},
            "required": ["url"],
        },
    },
    {
        "name": "compute_projection",
        "description": "Run the deterministic Nibud-based projection over current profile + bunq state. Read-only.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "update_target_property",
        "description": (
            "Update the user's target property by fetching a new Funda listing. "
            "This persists the change to the user's profile and recalculates projections. "
            "Use when the user pastes a new Funda URL or asks to change their target property."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Funda listing URL"},
                "price_override_eur": {"type": "number", "description": "Manual price override if extraction fails"},
            },
            "required": ["url"],
        },
    },
    {
        "name": "propose_move_money",
        "description": "Propose moving money between two of the user's bunq buckets. WRITE ACTION — requires user approval before execution.",
        "input_schema": {
            "type": "object",
            "properties": {
                "from_bucket_id": {"type": "string"},
                "to_bucket_id": {"type": "string"},
                "amount_eur": {"type": "number", "exclusiveMinimum": 0},
                "reason": {"type": "string"},
            },
            "required": ["from_bucket_id", "to_bucket_id", "amount_eur", "reason"],
        },
    },
    {
        "name": "propose_create_bucket",
        "description": "Propose creating a new bunq Savings bucket. WRITE ACTION — requires user approval.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "target_eur": {"type": "number", "exclusiveMinimum": 0},
                "reason": {"type": "string"},
            },
            "required": ["name", "reason"],
        },
    },
]

READ_TOOLS = {"get_bunq_transactions", "get_bunq_buckets", "get_funda_property", "compute_projection", "update_target_property"}

KNOWN_TOOLS = {t["name"] for t in TOOL_SCHEMAS}


def is_read_only(name: str) -> bool:
    """True if the tool auto-executes without user approval."""
    return not name.startswith("propose_")


@dataclass
class ToolContext:
    bunq_client: Any  # BunqClient from backend.bunq_client
    storage: Any      # Storage from backend.storage.base
    user_id: str


def _truncate_result(data: dict, max_chars: int = 2000) -> dict:
    """Trim transaction lists until the JSON representation fits within max_chars."""
    serialized = json.dumps(data)
    if len(serialized) <= max_chars:
        return data

    if "transactions" not in data:
        return data

    transactions = list(data["transactions"])
    while transactions and len(json.dumps({**data, "transactions": transactions})) > max_chars:
        transactions = transactions[1:]  # drop oldest (front of list)

    return {**data, "transactions": transactions}


async def execute_read_tool(name: str, params: dict, ctx: ToolContext) -> dict:
    """Dispatch a read-only tool call and return its result as a dict."""
    assert name in READ_TOOLS, f"Tool is not read-only: {name}"

    if name not in KNOWN_TOOLS:
        raise ValueError(f"Unknown read tool: {name}")

    if name == "get_bunq_transactions":
        raw = await ctx.bunq_client.get_transactions()
        result = {
            "transactions": raw.get("transactions", []),
            "total_count": len(raw.get("transactions", [])),
            "window_days": params["window_days"],
        }
        return _truncate_result(result)

    if name == "get_bunq_buckets":
        buckets = await ctx.bunq_client.get_buckets()
        return {"buckets": buckets}

    if name == "get_funda_property":
        from backend.funda import parse_funda  # noqa: PLC0415
        return await parse_funda(params["url"])

    if name == "compute_projection":
        profile = ctx.storage.get_profile(ctx.user_id)
        if profile is None:
            return {"error": "No profile found for user"}
        raw = await ctx.bunq_client.get_transactions()
        transactions = raw.get("transactions", [])
        buckets = await ctx.bunq_client.get_buckets()
        projection = _compute_projection(profile, transactions, buckets)
        return projection.model_dump()

    if name == "update_target_property":
        return await _update_target_property(params, ctx)

    raise ValueError(f"Unknown read tool: {name}")


async def _update_target_property(params: dict, ctx: ToolContext) -> dict:
    """Parse a new Funda listing, update the user's profile target, and recalculate projections."""
    from backend.funda import parse_funda  # noqa: PLC0415
    from backend.models import Target  # noqa: PLC0415

    profile = ctx.storage.get_profile(ctx.user_id)
    if profile is None:
        return {"error": "No profile found for user"}

    url = params["url"]
    funda_data = await parse_funda(url)

    price_eur = params.get("price_override_eur") or funda_data.get("price_eur")
    if price_eur is None:
        return {"error": "Could not determine property price. Ask the user for a manual price."}

    now_ms = int(time.time() * 1000)
    profile.target = Target(
        funda_url=url,
        price_eur=float(price_eur),
        address=funda_data.get("address") or "",
        type=funda_data.get("type"),
        size_m2=funda_data.get("size_m2"),
        year_built=funda_data.get("year_built"),
        fetched_at=now_ms,
    )

    raw = await ctx.bunq_client.get_transactions()
    transactions = raw.get("transactions", [])
    buckets = await ctx.bunq_client.get_buckets()
    projection = _compute_projection(profile, transactions, buckets)
    profile.projection = projection
    ctx.storage.upsert_profile(profile)

    return {
        "updated": True,
        "target": {
            "funda_url": profile.target.funda_url,
            "price_eur": profile.target.price_eur,
            "address": profile.target.address,
        },
        "projection": projection.model_dump(),
    }
