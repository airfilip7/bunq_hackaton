"""SSE agent loop for the bunq Nest chat agent."""

from __future__ import annotations

import json
import logging
import time
from typing import Awaitable, Callable

import ulid

from backend.agent.system_prompt import build_system_prompt
from backend.agent.tools import TOOL_SCHEMAS, execute_read_tool, is_read_only, ToolContext
from backend.anthropic_client import stream_chat
from backend.bunq_client import BunqClient
from backend.models import PendingTool, Turn

logger = logging.getLogger(__name__)

SseEmit = Callable[[str, dict], Awaitable[None]]

MAX_TOOL_ROUNDS = 10


def validate_overrides(tool_name: str, params: dict, overrides: dict) -> dict:
    """Validate override keys/types against the tool's input_schema and return merged params.

    Raises ValueError with a clear message if validation fails.
    """
    schema = next((t["input_schema"] for t in TOOL_SCHEMAS if t["name"] == tool_name), None)
    if schema is None:
        raise ValueError(f"Unknown tool: {tool_name}")

    properties = schema.get("properties", {})

    for key, value in overrides.items():
        if key not in properties:
            raise ValueError(f"Override key '{key}' is not allowed for tool '{tool_name}'")

        expected_type = properties[key].get("type")
        if expected_type == "string" and not isinstance(value, str):
            raise ValueError(f"Override key '{key}' must be a string, got {type(value).__name__}")
        if expected_type == "number" and not isinstance(value, (int, float)):
            raise ValueError(f"Override key '{key}' must be a number, got {type(value).__name__}")
        if expected_type in ("number", "integer"):
            exclusive_minimum = properties[key].get("exclusiveMinimum")
            if exclusive_minimum is not None and value <= exclusive_minimum:
                raise ValueError(
                    f"Override key '{key}' must be > {exclusive_minimum}, got {value}"
                )

    return {**params, **overrides}


def turns_to_messages(turns: list[Turn]) -> list[dict]:
    """Convert stored Turn objects to Anthropic messages format with strict alternation."""
    raw: list[dict] = []

    for turn in turns:
        if turn.kind == "user_message":
            raw.append({"role": "user", "content": turn.content or ""})

        elif turn.kind == "assistant_message":
            blocks: list[dict] = []
            if turn.content:
                blocks.append({"type": "text", "text": turn.content})
            for tu in turn.tool_uses or []:
                blocks.append({
                    "type": "tool_use",
                    "id": tu["id"],
                    "name": tu["name"],
                    "input": tu["input"],
                })
            raw.append({"role": "assistant", "content": blocks})

        elif turn.kind == "tool_result":
            raw.append({
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": turn.tool_use_id,
                        "content": json.dumps(turn.result),
                    }
                ],
            })

        elif turn.kind == "tool_approval":
            continue  # skip

    # Merge consecutive same-role messages
    merged: list[dict] = []
    for msg in raw:
        if merged and merged[-1]["role"] == msg["role"]:
            # Normalise both to lists
            prev_content = merged[-1]["content"]
            if isinstance(prev_content, str):
                prev_content = [{"type": "text", "text": prev_content}]

            new_content = msg["content"]
            if isinstance(new_content, str):
                new_content = [{"type": "text", "text": new_content}]

            merged[-1] = {"role": msg["role"], "content": prev_content + new_content}
        else:
            # Ensure content is always a list (Anthropic prefers it)
            content = msg["content"]
            if isinstance(content, str):
                content = [{"type": "text", "text": content}]
            merged.append({"role": msg["role"], "content": content})

    return merged


async def execute_write_tool(tool_name: str, params: dict, bunq_client: BunqClient) -> dict:
    """Dispatch an approved write tool call."""
    try:
        if tool_name == "propose_move_money":
            ref = await bunq_client.move_money(
                params["from_bucket_id"],
                params["to_bucket_id"],
                params["amount_eur"],
            )
            return {"ok": True, "execution_ref": ref}

        if tool_name == "propose_create_bucket":
            bucket = await bunq_client.create_bucket(
                params["name"],
                params.get("target_eur", 0),
            )
            return {"ok": True, "bucket": bucket}

        return {"ok": False, "error": f"Unknown write tool: {tool_name}"}

    except Exception as e:
        return {"ok": False, "error": str(e)}


def _make_turn(session_id: str, **kwargs) -> Turn:
    return Turn(
        turn_id=str(ulid.ULID()),
        session_id=session_id,
        ts_ms=int(time.time() * 1000),
        **kwargs,
    )


async def run_turn(
    session_id: str,
    inbound: dict,
    storage,
    bunq_client: BunqClient,
    user_id: str,
    sse_emit: SseEmit,
) -> None:
    # ── Step 1: Persist inbound Turn ────────────────────────────────────────
    turn_type = inbound.get("type")

    if turn_type == "user_message":
        turn = _make_turn(session_id, kind="user_message", content=inbound["content"])
        storage.append_turn(session_id, turn)

    elif turn_type == "tool_approval":
        turn = _make_turn(
            session_id,
            kind="tool_approval",
            tool_use_id=inbound.get("tool_use_id"),
            decision=inbound.get("decision"),
            overrides=inbound.get("overrides"),
            feedback=inbound.get("feedback"),
        )
        storage.append_turn(session_id, turn)

    # ── Step 2: Resolve pending tool if this is an approval ─────────────────
    if turn_type == "tool_approval":
        tool_use_id = inbound.get("tool_use_id")
        decision = inbound.get("decision")

        pending = storage.get_pending_tool(session_id, tool_use_id)
        if pending is None:
            await sse_emit("error", {"message": "No matching pending action.", "retryable": False})
            return

        if decision == "approve":
            try:
                params = validate_overrides(
                    pending.tool_name, pending.params, inbound.get("overrides") or {}
                )
            except ValueError as exc:
                await sse_emit("error", {"message": str(exc), "retryable": False})
                storage.clear_pending_tool(session_id, pending.tool_use_id)
                return

            result_data = await execute_write_tool(pending.tool_name, params, bunq_client)
            await sse_emit(
                "tool_result",
                {
                    "tool_use_id": pending.tool_use_id,
                    "ok": result_data.get("ok", False),
                    "summary": json.dumps(result_data)[:200],
                },
            )
        else:
            result_data = {
                "declined_by_user": True,
                "feedback": inbound.get("feedback", ""),
            }

        result_turn = _make_turn(
            session_id,
            kind="tool_result",
            tool_use_id=pending.tool_use_id,
            tool_name=pending.tool_name,
            ok=result_data.get("ok"),
            result=result_data,
        )
        storage.append_turn(session_id, result_turn)
        storage.clear_pending_tool(session_id, pending.tool_use_id)
        # fall through to model call

    # ── Step 3: Build context ────────────────────────────────────────────────
    turns = storage.list_turns(session_id, include_hidden=True)
    messages = turns_to_messages(turns)
    system = build_system_prompt(user_id, storage)
    tools = TOOL_SCHEMAS
    ctx = ToolContext(bunq_client=bunq_client, storage=storage, user_id=user_id)

    # ── Step 4: Model loop ───────────────────────────────────────────────────
    logger.info("run_turn: starting model loop for session=%s", session_id)

    for _round in range(MAX_TOOL_ROUNDS):
        text_buffer = ""
        tool_uses_in_this_pass: list[dict] = []
        tool_input_buffers: dict[int, list[str]] = {}
        tool_blocks: dict[int, dict] = {}

        logger.info(
            "model_call_start session=%s round=%d messages=%d tools=%d",
            session_id, _round, len(messages), len(tools),
        )
        call_start = time.time()

        try:
            async with stream_chat(system, messages, tools) as stream:
                async for event in stream:
                    if event.type == "content_block_start":
                        block = event.content_block
                        if block.type == "tool_use":
                            tool_blocks[event.index] = {"id": block.id, "name": block.name}
                            tool_input_buffers[event.index] = []

                    elif event.type == "content_block_delta":
                        delta = event.delta
                        if delta.type == "text_delta":
                            text_buffer += delta.text
                            await sse_emit("delta", {"text": delta.text})
                        elif delta.type == "input_json_delta":
                            tool_input_buffers[event.index].append(delta.partial_json)

                    elif event.type == "content_block_stop":
                        if event.index in tool_blocks:
                            raw_json = "".join(tool_input_buffers.get(event.index, []))
                            try:
                                parsed_input = json.loads(raw_json) if raw_json else {}
                            except json.JSONDecodeError:
                                parsed_input = {}
                            tb = tool_blocks[event.index]
                            tool_uses_in_this_pass.append({
                                "id": tb["id"],
                                "name": tb["name"],
                                "input": parsed_input,
                            })

        except Exception as exc:
            call_ms = int((time.time() - call_start) * 1000)
            logger.info(
                "model_call_error session=%s round=%d latency_ms=%d error=%s",
                session_id, _round, call_ms, str(exc)[:200],
            )
            logger.exception("run_turn: stream error in round %d", _round)
            if text_buffer:
                err_turn = _make_turn(
                    session_id,
                    kind="assistant_message",
                    content=text_buffer,
                )
                storage.append_turn(session_id, err_turn)
            await sse_emit("error", {"message": str(exc), "retryable": True})
            return

        call_ms = int((time.time() - call_start) * 1000)
        logger.info(
            "model_call_end session=%s round=%d latency_ms=%d text_len=%d tool_uses=%d",
            session_id, _round, call_ms, len(text_buffer), len(tool_uses_in_this_pass),
        )

        # ── No tool uses: done ───────────────────────────────────────────────
        if not tool_uses_in_this_pass:
            asst_turn = _make_turn(
                session_id,
                kind="assistant_message",
                content=text_buffer or None,
            )
            storage.append_turn(session_id, asst_turn)
            await sse_emit("done", {"reason": "complete"})
            return

        # ── Has tool uses: persist assistant turn ────────────────────────────
        asst_turn = _make_turn(
            session_id,
            kind="assistant_message",
            content=text_buffer or None,
            tool_uses=tool_uses_in_this_pass,
        )
        storage.append_turn(session_id, asst_turn)

        # Check if any tool is a write tool — if so, propose it
        write_tool = next(
            (tu for tu in tool_uses_in_this_pass if not is_read_only(tu["name"])), None
        )

        if write_tool is not None:
            # Write tool — propose and wait for approval
            logger.info("run_turn: proposing write tool %s", write_tool["name"])
            logger.info(
                "write_tool_proposed session=%s tool=%s params_keys=%s",
                session_id, write_tool["name"], ",".join(write_tool["input"].keys()),
            )
            pending = PendingTool(
                tool_use_id=write_tool["id"],
                session_id=session_id,
                tool_name=write_tool["name"],
                params=write_tool["input"],
                summary=write_tool["input"].get("reason", ""),
                rationale=write_tool["input"].get("reason", ""),
                risk_level="low",
                proposed_at=int(time.time() * 1000),
            )
            storage.put_pending_tool(session_id, pending)

            await sse_emit(
                "tool_proposal",
                {
                    "tool_use_id": write_tool["id"],
                    "name": write_tool["name"],
                    "params": write_tool["input"],
                    "summary": pending.summary,
                    "rationale": pending.rationale,
                    "risk_level": pending.risk_level,
                },
            )
            await sse_emit("done", {"reason": "awaiting_approval"})
            return

        # All tools are read-only — execute each one
        for tu in tool_uses_in_this_pass:
            logger.info("run_turn: executing read tool %s", tu["name"])
            await sse_emit("tool_call", {"tool_use_id": tu["id"], "name": tu["name"], "params": tu["input"], "kind": "read"})

            tool_t0 = time.time()
            try:
                result = await execute_read_tool(tu["name"], tu["input"], ctx)
            except Exception as exc:
                result = {"error": str(exc)}

            tool_ms = int((time.time() - tool_t0) * 1000)
            summary = json.dumps(result)[:200]
            logger.info(
                "read_tool_done session=%s tool=%s latency_ms=%d result_size=%d",
                session_id, tu["name"], tool_ms, len(summary),
            )
            await sse_emit(
                "tool_result",
                {"tool_use_id": tu["id"], "ok": True, "summary": summary},
            )

            result_turn = _make_turn(
                session_id,
                kind="tool_result",
                tool_use_id=tu["id"],
                tool_name=tu["name"],
                ok=True,
                result=result,
            )
            storage.append_turn(session_id, result_turn)

        # Reload messages and continue loop
        turns = storage.list_turns(session_id, include_hidden=True)
        messages = turns_to_messages(turns)
        continue

    # MAX_TOOL_ROUNDS exhausted
    logger.warning("run_turn: max tool rounds reached for session=%s", session_id)
    await sse_emit("done", {"reason": "complete"})
