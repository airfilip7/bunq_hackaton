from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse, ServerSentEvent

from backend.agent.runner import run_turn
from backend.deps import get_bunq_client, get_current_user_id, get_storage

router = APIRouter()


class TurnRequest(BaseModel):
    type: str  # "user_message" | "tool_approval"
    content: str | None = None
    tool_use_id: str | None = None
    decision: str | None = None  # "approve" | "deny"
    overrides: dict | None = None
    feedback: str | None = None


@router.get("/sessions")
def list_sessions(
    user_id: str = Depends(get_current_user_id),
    storage=Depends(get_storage),
):
    sessions = storage.list_sessions(user_id, limit=20)
    return {"sessions": [s.model_dump() for s in sessions]}


@router.get("/sessions/{session_id}")
def get_session(
    session_id: str,
    user_id: str = Depends(get_current_user_id),
    storage=Depends(get_storage),
):
    session = storage.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.user_id != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    turns = storage.list_turns(session_id, include_hidden=False)
    return {"session": session.model_dump(), "turns": [t.model_dump() for t in turns]}


@router.post("/sessions/{session_id}/turns")
async def create_turn(
    session_id: str,
    body: TurnRequest,
    user_id: str = Depends(get_current_user_id),
    storage=Depends(get_storage),
    bunq_client=Depends(get_bunq_client),
):
    session = storage.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.user_id != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    if body.type == "user_message" and not body.content:
        raise HTTPException(status_code=400, detail="content required for user_message")
    if body.type == "tool_approval" and not body.tool_use_id:
        raise HTTPException(status_code=400, detail="tool_use_id required for tool_approval")
    if body.type not in ("user_message", "tool_approval"):
        raise HTTPException(status_code=400, detail=f"Unknown turn type: {body.type!r}")

    queue: asyncio.Queue[ServerSentEvent | None] = asyncio.Queue()

    async def sse_emit(event: str, data: dict) -> None:
        await queue.put(ServerSentEvent(data=json.dumps(data), event=event))

    async def run_agent():
        try:
            await run_turn(
                session_id=session_id,
                inbound=body.model_dump(),
                storage=storage,
                bunq_client=bunq_client,
                user_id=user_id,
                sse_emit=sse_emit,
            )
        except Exception as exc:
            await sse_emit("error", {"message": str(exc)})
        finally:
            await queue.put(None)

    async def event_generator():
        task = asyncio.create_task(run_agent())
        while True:
            item = await queue.get()
            if item is None:
                break
            yield item
        await task

    return EventSourceResponse(
        event_generator(),
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-store"},
        ping=15,
    )
