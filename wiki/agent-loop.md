# Chat agent — turn lifecycle

This is the part of the system that's easiest to get wrong. It encodes how the agent talks to the user, asks for more information when it needs it, and asks for approval before doing anything that changes money. Read this together with `architecture.md`.

---

## 1. The mental model

A *turn* is one HTTP request from the browser that returns an SSE stream. Inside that stream, the server runs the Anthropic tool-use loop until it hits one of three end-states:

| End-state | What happened | What the user sees |
|---|---|---|
| `complete` | Agent emitted a normal text response and stopped | A streamed message, conversation idle |
| `awaiting_user` | Agent asked a clarifying question (text only, no tool call) | A streamed message ending in a question; input box focused |
| `awaiting_approval` | Agent called a `propose_*` write tool | A streamed message + an inline approval card with action details |

The browser then waits for the user to do something. Whatever the user does — type a reply, approve, deny — turns into the *next* `POST` to the same endpoint, which opens a new SSE stream and continues the conversation. State lives in DynamoDB between turns.

This means: **there is no special "ask user" plumbing.** Asking the user is just the agent emitting text and stopping. The browser already has an input box. The "more context from the user" pattern collapses into the normal turn cycle.

The only thing that needs special handling is **write actions**, which always go through the approval lane.

---

## 2. The endpoint

```
POST /chat/sessions/{session_id}/turns
Content-Type: application/json
Accept: text/event-stream
```

### Request bodies (one of)

```jsonc
// 1. Plain user message — the dominant case
{ "type": "user_message", "content": "How much should I save monthly?" }

// 2. Approval response to a pending tool proposal
{ "type": "tool_approval",
  "tool_use_id": "tu_01abc...",
  "decision": "approve",
  "overrides": { "amount_eur": 250 }   // optional — user edited a parameter
}

// 3. Denial — the user said no
{ "type": "tool_approval",
  "tool_use_id": "tu_01abc...",
  "decision": "deny",
  "feedback": "Not yet — I want to keep that buffer."
}
```

The server:

1. Loads the session and verifies the user owns it (Cognito JWT → `user_id`, compared to `Sessions.user_id`).
2. Persists the inbound event as an append-only row in `Turns`.
3. If this is an approval, executes the bunq side-effect *now* (before the model runs again), persists a `TOOL_RESULT` row, and constructs a synthetic Anthropic `tool_result` block to feed into the model.
4. Loads conversation history, opens a Bedrock streaming call to Sonnet 4.6, and runs the agent loop (below).

### Response — Server-Sent Events

Each event is a JSON object on a single line.

```
event: delta
data: {"text": "Looking at your last six months "}

event: delta
data: {"text": "of transactions, I can see..."}

event: tool_call
data: {"tool_use_id": "tu_01...", "name": "get_bunq_transactions", "params": {"window_days": 180}, "kind": "read"}

event: tool_result
data: {"tool_use_id": "tu_01...", "ok": true, "summary": "180 days, 412 transactions"}

event: delta
data: {"text": "Your average savings rate is €1,450 / month..."}

event: tool_proposal
data: {"tool_use_id": "tu_02...", "name": "propose_move_money",
       "params": {"from_bucket": "Buffer", "to_bucket": "House", "amount_eur": 200},
       "summary": "Move €200 from Buffer to House — at current pace this shaves ~3 weeks off the timeline.",
       "risk_level": "low",
       "rationale": "You've kept Buffer above target for 3 months."}

event: done
data: {"reason": "awaiting_approval"}
```

### Headers

`X-Accel-Buffering: no` to defeat any reverse-proxy buffering. `Cache-Control: no-store`. Heartbeat `: ping` comments every 15s to keep the connection alive through ALB idle timeouts.

---

## 3. The server-side loop

```python
# pseudocode
async def run_turn(session_id, inbound_event, sse):
    persist(inbound_event)

    # Resolve any approval into a tool_result the model can consume.
    if inbound_event.type == "tool_approval":
        proposal = load_pending_tool(session_id, inbound_event.tool_use_id)
        if inbound_event.decision == "approve":
            params = {**proposal.params, **(inbound_event.overrides or {})}
            result = await bunq_client.execute(proposal.name, params)
            sse.emit("tool_result", {...})
        else:
            result = {"declined_by_user": True, "feedback": inbound_event.feedback}
        persist_tool_result(proposal, result)
        clear_pending_tool(session_id, inbound_event.tool_use_id)

    history = load_history(session_id)            # [{role, content/tool blocks}]
    system_prompt = SYSTEM_PROMPT_COACH            # the Wft-safe one
    tools = TOOL_SCHEMAS

    while True:
        async for chunk in bedrock.messages_stream(
            model="anthropic.claude-sonnet-4-6-v1:0",   # confirm at build time
            system=system_prompt,
            messages=history,
            tools=tools,
        ):
            if chunk.kind == "text_delta":
                sse.emit("delta", {"text": chunk.text})
                buffer_text(chunk.text)
            elif chunk.kind == "tool_use":
                tool_use = chunk.tool_use
                history.append(asst_with_tool_use(tool_use, buffer_text))

                if is_read_only(tool_use.name):
                    sse.emit("tool_call", {..., "kind": "read"})
                    result = await execute_read_tool(tool_use)
                    sse.emit("tool_result", {...})
                    history.append(user_with_tool_result(tool_use.id, result))
                    break  # break out of the inner stream, restart the model loop

                else:  # propose_* — write
                    persist_pending_tool(session_id, tool_use)
                    sse.emit("tool_proposal", {...})
                    sse.emit("done", {"reason": "awaiting_approval"})
                    return

            elif chunk.kind == "stop":
                if had_tool_use_in_this_pass:
                    continue  # let the inner stream finish, then loop
                # Pure text turn — model is done speaking.
                sse.emit("done", {"reason": "complete"})
                # If the last buffered text ends with a question and no tool call,
                # the front-end will treat reason=complete the same as awaiting_user.
                # (We don't try to detect questions server-side — it's the user's job
                # to decide whether to reply, and the front-end always shows the input.)
                return
```

A few things worth calling out:

- **The "ask user for more info" pattern is not a special event type.** Claude is genuinely good at asking a focused question when it needs one — we just let it speak text and stop. The frontend always renders an input box once the stream ends. If we ever needed structured asks (multiple choice, file upload), we'd add a `propose_*` style read-only `ask_user` tool — but for the hackathon, plain text is plenty.
- **Read tools auto-loop.** The user sees `tool_call` and `tool_result` events for transparency, but doesn't have to do anything. The model continues reasoning in the same SSE stream.
- **Write tools always pause.** `is_read_only` is a hard list keyed off tool name prefix (`propose_*` = write). Even if a future model ignores the `propose_` framing and tries to invoke a write directly, the runner refuses it. This is the safety boundary.
- **One pending approval at a time per session.** If the agent emits a proposal, the loop returns. The next turn must be an approval (or a denial, or — escape hatch — a new user message that the server interprets as "cancel the pending action").

---

## 4. Tool schemas (initial set)

```jsonc
[
  { "name": "get_bunq_transactions",
    "description": "Recent transactions for the user's monetary accounts. Read-only.",
    "input_schema": { "type": "object",
      "properties": { "window_days": { "type": "integer", "minimum": 1, "maximum": 365 } },
      "required": ["window_days"] } },

  { "name": "get_bunq_buckets",
    "description": "Current Savings buckets and balances. Read-only.",
    "input_schema": { "type": "object", "properties": {} } },

  { "name": "get_funda_property",
    "description": "Re-fetch the user's target Funda listing.",
    "input_schema": { "type": "object",
      "properties": { "url": { "type": "string" } },
      "required": ["url"] } },

  { "name": "compute_projection",
    "description": "Run the deterministic Nibud-based projection over current profile + bunq state. Read-only.",
    "input_schema": { "type": "object", "properties": {} } },

  { "name": "propose_move_money",
    "description": "Propose moving money between two of the user's bunq buckets. WRITE ACTION — requires user approval before execution.",
    "input_schema": { "type": "object",
      "properties": {
        "from_bucket_id": { "type": "string" },
        "to_bucket_id":   { "type": "string" },
        "amount_eur":     { "type": "number", "exclusiveMinimum": 0 },
        "reason":         { "type": "string" }
      },
      "required": ["from_bucket_id", "to_bucket_id", "amount_eur", "reason"] } },

  { "name": "propose_create_bucket",
    "description": "Propose creating a new bunq Savings bucket. WRITE ACTION — requires user approval.",
    "input_schema": { "type": "object",
      "properties": {
        "name":           { "type": "string" },
        "target_eur":     { "type": "number", "exclusiveMinimum": 0 },
        "reason":         { "type": "string" }
      },
      "required": ["name", "reason"] } }
]
```

The system prompt instructs the agent to *always* call `propose_*` tools rather than describing the action in prose; the runner enforces it on the tool side.

---

## 5. The approval card — what the frontend renders

When the SSE stream ends with `tool_proposal`, the chat UI appends a card below the agent's last text:

```
┌──────────────────────────────────────────────────────────┐
│  Suggested action — needs your approval                   │
│                                                          │
│  Move €200 from Buffer → House                            │
│  Reason: at current pace this shaves ~3 weeks off the    │
│  timeline.                                                │
│                                                          │
│  [ Approve ]  [ Edit amount ]  [ Not now ]                │
└──────────────────────────────────────────────────────────┘
```

- **Approve** → POST `tool_approval` with `decision=approve`, no overrides.
- **Edit amount** → inline number input → POST with `overrides`.
- **Not now** → POST with `decision=deny`, `feedback` optional.

The user can also keep typing a normal message; the frontend interprets that as an implicit denial *plus* a follow-up — sent as two events back-to-back, denial first.

---

## 6. Failure modes and how they're handled

| Failure | Behaviour |
|---|---|
| Bedrock 4xx (token / model id wrong) | Loop bails, emits `event: error`, persists the partial assistant message so the user doesn't lose context. |
| Bedrock 5xx mid-stream | Same; UI shows "connection hiccup, retry?" — retry replays the same inbound event from DynamoDB. |
| bunq API failure during an approved write | The `tool_result` carries `ok: false, error: ...` back into the model, which then explains the failure to the user. **The pending-tool row is cleared either way** so we never double-execute on retry. |
| User closes the tab while a proposal is pending | The `PENDING_TOOL` row stays. Next session open, the frontend reads it and re-renders the approval card. |
| Two browser tabs open at the same session | Idempotency: every `POST /turns` carries a client-generated `idempotency_key`. Server dedupes for 60s. |
| Race between user typing and an arriving tool proposal | The user's message becomes the next turn; on receiving it, the server clears the pending tool with an implicit denial and processes the message normally. |
| Cognito token expired mid-stream | 401, frontend silently refreshes, replays the inbound event. |

---

## 7. The system prompt (where it lives)

The Wft-safe coaching system prompt from `CLAUDE.md` is canonical. It's imported from `backend/prompts.py` by the agent runner — no second copy. The prompt is augmented at runtime with:

- The user's profile snapshot (payslip extract, target property, current bunq state summary).
- The Nibud norms for the current year (loaded once at server start).
- A short list of the available tools and a strict reminder: *for any action that changes money, you MUST call a `propose_*` tool. Do not describe the action in prose. The user only sees what you do via tools.*

The augmentation lives in a single `build_system_prompt(user_id)` function so it's testable.

---

## 8. Why this pattern is right for us

- **It's the same shape as Anthropic's documented tool-use loop.** No invention, no surprises.
- **It survives reloads.** All state in DynamoDB; the agent is fully resumable.
- **It separates safety from cleverness.** The model can be as agentic as it wants; the runner is the one that enforces the read/write split. If we ever swap the model, the safety boundary doesn't move.
- **The "ask user" case is free.** Plain text reply, plain text response. No special UI, no special protocol.
- **The streaming UX is the demo's magic moment.** SSE deltas + a popping approval card on top is exactly the kind of thing that lands well on stage.

---

## 9. What this doc deliberately leaves to the implementer

- The exact Bedrock model id string (Sonnet 4.6 availability on Bedrock — confirm at build time; fall back to current Sonnet vision otherwise).
- Frontend component decomposition. The contract above is enough.
- Exact DynamoDB conditional expressions for write-once turn ordering (`turn_id` is a UUID v7; `SK = TURN#{epoch_ms}#{turn_id}` is naturally sortable).
- Rate limiting. Cognito + per-user-per-minute is enough for a demo.
