"""DynamoDB client and typed helpers for the bunq-nest-main single-table design."""
import time
import uuid
from typing import Any

import boto3
from boto3.dynamodb.conditions import Key

from backend.config import settings

_resource = None


def _get_resource():
    global _resource
    if _resource is None:
        _resource = boto3.resource(
            "dynamodb",
            region_name=settings.aws_region,
        )
    return _resource


def _table():
    return _get_resource().Table(settings.dynamo_table)


# ── helpers ──────────────────────────────────────────────────────────────────

def _now_ms() -> int:
    return int(time.time() * 1000)


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


# ── User profile ──────────────────────────────────────────────────────────────

def get_profile(user_id: str) -> dict | None:
    resp = _table().get_item(Key={"PK": f"USER#{user_id}", "SK": "PROFILE"})
    return resp.get("Item")


def put_profile(user_id: str, email: str) -> dict:
    item = {
        "PK": f"USER#{user_id}",
        "SK": "PROFILE",
        "user_id": user_id,
        "email": email,
        "onboarded_at": None,
        "payslip": None,
        "target": None,
        "projection": None,
        "schema_version": 1,
    }
    _table().put_item(Item=item, ConditionExpression="attribute_not_exists(PK)")
    return item


def update_profile(user_id: str, updates: dict[str, Any]) -> None:
    expr_parts = []
    names: dict[str, str] = {}
    values: dict[str, Any] = {}
    for i, (k, v) in enumerate(updates.items()):
        placeholder = f"#a{i}"
        val_placeholder = f":v{i}"
        names[placeholder] = k
        values[val_placeholder] = v
        expr_parts.append(f"{placeholder} = {val_placeholder}")
    _table().update_item(
        Key={"PK": f"USER#{user_id}", "SK": "PROFILE"},
        UpdateExpression="SET " + ", ".join(expr_parts),
        ExpressionAttributeNames=names,
        ExpressionAttributeValues=values,
    )


# ── Sessions ──────────────────────────────────────────────────────────────────

def create_session(user_id: str) -> dict:
    session_id = _new_id("s")
    now = _now_ms()
    item = {
        "PK": f"USER#{user_id}",
        "SK": f"SESSION#{session_id}",
        "GSI1PK": f"USER#{user_id}",
        "GSI1SK": f"LAST_ACTIVE#{now:020d}",
        "session_id": session_id,
        "user_id": user_id,
        "started_at": now,
        "last_active_at": now,
        "state": "active",
    }
    _table().put_item(Item=item)
    return item


def get_latest_session(user_id: str) -> dict | None:
    resp = _table().query(
        IndexName="GSI1",
        KeyConditionExpression=Key("GSI1PK").eq(f"USER#{user_id}"),
        ScanIndexForward=False,
        Limit=1,
    )
    items = resp.get("Items", [])
    return items[0] if items else None


def list_sessions(user_id: str) -> list[dict]:
    resp = _table().query(
        IndexName="GSI1",
        KeyConditionExpression=Key("GSI1PK").eq(f"USER#{user_id}"),
        ScanIndexForward=False,
    )
    return resp.get("Items", [])


def touch_session(user_id: str, session_id: str) -> None:
    now = _now_ms()
    _table().update_item(
        Key={"PK": f"USER#{user_id}", "SK": f"SESSION#{session_id}"},
        UpdateExpression="SET last_active_at = :t, GSI1SK = :gsk",
        ExpressionAttributeValues={
            ":t": now,
            ":gsk": f"LAST_ACTIVE#{now:020d}",
        },
    )


# ── Turns ─────────────────────────────────────────────────────────────────────

def append_turn(session_id: str, kind: str, payload: dict) -> dict:
    now = _now_ms()
    turn_id = _new_id("t")
    item = {
        "PK": f"SESSION#{session_id}",
        "SK": f"TURN#{now:020d}#{turn_id}",
        "kind": kind,
        **payload,
    }
    _table().put_item(Item=item)
    return item


def list_turns(session_id: str) -> list[dict]:
    resp = _table().query(
        KeyConditionExpression=(
            Key("PK").eq(f"SESSION#{session_id}") &
            Key("SK").begins_with("TURN#")
        ),
        ScanIndexForward=True,
    )
    return resp.get("Items", [])


# ── Tool runs ─────────────────────────────────────────────────────────────────

def put_tool_run(session_id: str, tool_use_id: str, payload: dict) -> None:
    _table().put_item(Item={
        "PK": f"SESSION#{session_id}",
        "SK": f"TOOLRUN#{tool_use_id}",
        "tool_use_id": tool_use_id,
        **payload,
    })


# ── Pending tool (write-action approval gate) ─────────────────────────────────

def put_pending_tool(session_id: str, tool_use_id: str, payload: dict) -> None:
    _table().put_item(Item={
        "PK": f"SESSION#{session_id}",
        "SK": f"PENDING_TOOL#{tool_use_id}",
        "tool_use_id": tool_use_id,
        "proposed_at": _now_ms(),
        **payload,
    })


def get_pending_tool(session_id: str, tool_use_id: str) -> dict | None:
    resp = _table().get_item(
        Key={"PK": f"SESSION#{session_id}", "SK": f"PENDING_TOOL#{tool_use_id}"}
    )
    return resp.get("Item")


def list_pending_tools(session_id: str) -> list[dict]:
    resp = _table().query(
        KeyConditionExpression=(
            Key("PK").eq(f"SESSION#{session_id}") &
            Key("SK").begins_with("PENDING_TOOL#")
        ),
    )
    return resp.get("Items", [])


def delete_pending_tool(session_id: str, tool_use_id: str) -> None:
    _table().delete_item(
        Key={"PK": f"SESSION#{session_id}", "SK": f"PENDING_TOOL#{tool_use_id}"}
    )


# ── bunq tokens ───────────────────────────────────────────────────────────────

def put_bunq_token(user_id: str, ciphertext_b64: str, kms_key_id: str, expires_at: int, scope: str = "read") -> None:
    _table().put_item(Item={
        "PK": f"USER#{user_id}",
        "SK": "BUNQ_TOKEN",
        "ciphertext_blob_b64": ciphertext_b64,
        "kms_key_id": kms_key_id,
        "expires_at": expires_at,
        "rotated_at": _now_ms(),
        "scope": scope,
    })


def get_bunq_token(user_id: str) -> dict | None:
    resp = _table().get_item(Key={"PK": f"USER#{user_id}", "SK": "BUNQ_TOKEN"})
    return resp.get("Item")
