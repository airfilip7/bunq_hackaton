# Backend implementation plan — bunq Nest

## Framing note

**Pragmatic path:** local FastAPI + Anthropic direct API + SQLite + fixture-mode bunq for speed of iteration. Each AWS service is a swap-in once the local version works (Phase 11). This matches the `[risk]` fallbacks in `architecture.md` and keeps every phase runnable.

---

## Phase 0 — Project bootstrap (45–60 min)

**Goal:** `uvicorn backend.main:app --reload` returns 200 on `GET /health`.

### Directory layout

```
backend/
├── __init__.py
├── main.py                # FastAPI app + router mount
├── config.py              # pydantic-settings, reads .env
├── deps.py                # FastAPI dependencies (auth, db, clients)
├── prompts.py             # canonical prompts (verbatim from CLAUDE.md)
├── models.py              # pydantic schemas for requests/responses
├── storage/
│   ├── __init__.py
│   ├── base.py            # abstract Storage protocol
│   ├── sqlite_store.py    # default for hackathon
│   └── dynamo_store.py    # stub, implement in Phase 11
├── anthropic_client.py
├── bunq_client.py
├── funda.py
├── projection.py
├── agent/
│   ├── __init__.py
│   ├── runner.py          # SSE agent loop
│   ├── tools.py           # tool schemas + dispatch
│   └── system_prompt.py   # build_system_prompt(user_id)
├── routes/
│   ├── __init__.py
│   ├── onboard.py
│   ├── chat.py
│   └── bunq_oauth.py
├── mocks/
│   ├── transactions.json
│   ├── buckets.json
│   └── funda_listings/    # cached HTML for the 3 demo URLs
└── tests/
    ├── test_projection.py
    ├── test_funda.py
    └── test_agent_loop.py
```

### Tasks

1. `pyproject.toml` deps: `fastapi`, `uvicorn[standard]`, `pydantic>=2`, `pydantic-settings`, `httpx`, `anthropic`, `sse-starlette`, `python-multipart`, `pyjwt`, `boto3`, `pytest`, `pytest-asyncio`, `beautifulsoup4`, `python-dotenv`, `Pillow`.
2. `.env.example`:
   ```
   ANTHROPIC_API_KEY=
   BUNQ_MODE=fixture
   STORAGE_BACKEND=sqlite
   SQLITE_PATH=./bunq_nest.db
   JWT_SECRET=
   DEMO_USER_ID=u_demo
   FUNDA_MODE=fixture
   DEMO_REPLAY=0
   ```
3. `backend/main.py`: create `FastAPI(title="bunq Nest")`, mount the three routers, add `GET /health → {"ok": True}`, enable CORS for `http://localhost:5173`.

### Pitfalls

- Don't add a Dockerfile yet. Container only when deploying.
- Don't use Alembic. SQLite tables are `CREATE TABLE IF NOT EXISTS` on startup.
- Pin `anthropic>=0.40` for streaming + tool-use API compatibility.

---

## Phase 1 — Auth stub + storage primitive (1h)

**Goal:** every protected route resolves to a `user_id`; we can read/write all entity types.

### Tasks

1. `backend/deps.py`:
   - `get_current_user_id(authorization: str = Header(...)) -> str`
   - **Hackathon shortcut:** if `Authorization: Bearer demo`, return `DEMO_USER_ID`. Else decode JWT. Mark with `# DEMO ONLY` comment.
   - `get_storage() -> Storage`

2. `backend/storage/base.py` — define `Storage` Protocol:
   ```python
   class Storage(Protocol):
       def get_profile(user_id: str) -> Profile | None
       def upsert_profile(profile: Profile) -> None
       def create_session(user_id: str) -> Session
       def get_latest_session(user_id: str) -> Session | None
       def touch_session(session_id: str) -> None
       def append_turn(session_id: str, turn: Turn) -> None
       def list_turns(session_id: str, include_hidden: bool = False) -> list[Turn]
       def put_pending_tool(session_id: str, pending: PendingTool) -> None
       def get_pending_tool(session_id: str, tool_use_id: str) -> PendingTool | None
       def clear_pending_tool(session_id: str, tool_use_id: str) -> None
       def get_bunq_token(user_id: str) -> BunqToken | None
       def put_bunq_token(user_id: str, token: BunqToken) -> None
   ```

3. `sqlite_store.py`: 5 tables — `profiles`, `sessions`, `turns`, `pending_tools`, `bunq_tokens`. Store JSON blobs in a `data TEXT` column; only index `user_id`, `session_id`, `tool_use_id`, `last_active_at`.

4. `backend/models.py` — pydantic models matching `data-model.md`:
   - `Profile`, `Payslip`, `Target`, `Projection`
   - `Session`
   - `Turn` (with `kind` discriminator: `user_message | assistant_message | tool_result | tool_approval`)
   - `PendingTool`, `BunqToken`

### Pitfalls

- **Turn ordering:** use ULIDs or UUID v7 for `turn_id`; store `ts_ms` as BIGINT; sort by `(ts_ms, turn_id)`. Don't rely on INSERT order.
- **Skip `tool_runs` table for MVP.** The `assistant_message` turn already carries `tool_uses` and `tool_result` turns carry results. No need for the duplicate row.
- The `Storage` Protocol is the abstraction boundary. No SQL outside `sqlite_store.py`.

---

## Phase 2 — Anthropic Bedrock client (30 min) ✅

**Goal:** one client shared by VLM extraction and the agent loop, running on Amazon Bedrock.

### Tasks

1. `backend/anthropic_client.py`:
   - `client = AsyncAnthropicBedrock(aws_region=settings.aws_region)` (module-level) — uses the standard AWS credential chain (env vars, `~/.aws/credentials`, IAM role)
   - `MODEL_VISION = settings.bedrock_vision_model` — configurable via env, defaults to `anthropic.claude-sonnet-4-6`
   - `MODEL_CHAT = settings.bedrock_chat_model` — same default
   - `async def extract_payslip(image_bytes: bytes, media_type: str) -> dict` — vision prompt from `prompts.py`, parse JSON response, raise `ExtractionError` on parse failure
   - `async def stream_chat(system: str, messages: list, tools: list)` — async context manager yielding raw SDK stream from `client.messages.stream(...)`

2. `backend/config.py` — added settings:
   - `aws_region: str = "us-east-1"`
   - `bedrock_vision_model: str = "anthropic.claude-sonnet-4-6"`
   - `bedrock_chat_model: str = "anthropic.claude-sonnet-4-6"`

3. `pyproject.toml` — changed `anthropic>=0.40` → `anthropic[bedrock]>=0.40`

### Pitfalls

- **AWS credentials** must be configured before running. Set `AWS_ACCESS_KEY_ID` + `AWS_SECRET_ACCESS_KEY` in env or configure `~/.aws/credentials`. No `ANTHROPIC_API_KEY` needed.
- **Bedrock model IDs** differ from direct API IDs. Default: `anthropic.claude-sonnet-4-6`. Override via `BEDROCK_VISION_MODEL` / `BEDROCK_CHAT_MODEL` env vars if needed.
- **Vision input format** must be:
  ```python
  content = [
      {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": b64}},
      {"type": "text", "text": prompt},
  ]
  ```
- **JSON fences in VLM output:** strip ` ```json ` / ` ``` ` before `json.loads`. The model ignores the "return ONLY valid JSON" instruction maybe 5% of the time.

---

## Phase 3 — Payslip extractor end-to-end (2h) ← RISKIEST, DO FIRST

**Goal:** POST a payslip image → get `{gross, net, employer, period, confidence}`.

### Tasks

1. `POST /onboard/upload-payslip` — accepts `multipart/form-data`, one image file.
   - **Hackathon shortcut:** receive image in backend, hold in memory, extract inline. Skip presigned S3 URLs until Phase 11.
2. Image normalization before VLM:
   - Resize to max 1568px long edge (Anthropic recommended max).
   - Strip EXIF.
   - Re-encode as JPEG quality 85.
3. Call `anthropic_client.extract_payslip(bytes, media_type)`.
4. Post-process numeric fields: normalize Dutch `4.850,00` → `4850.00` via regex before returning.
5. Return `{"payslip": {...}, "confidence": "high|medium|low"}`. Frontend shows manual-edit form when `confidence != "high"`.

### Pitfalls

- **Iterate the prompt against the real demo payslip ≥20 times** before moving on. This is the demo's magic moment — one failure on stage = demo dead. CLAUDE.md says this explicitly.
- **Dutch number formatting** (`4.850,00`) trips the model. Add: *"return numbers as plain decimals with `.` as the decimal separator"* to the prompt. Add a regex post-processor as a safety net.
- **HEIC files:** modern iPhone photos are HEIC. Either install `pillow-heif` or restrict the upload `accept` attribute on the frontend to `image/jpeg,image/png`. Decide before onboarding is built.

---

## Phase 4 — Funda parser (1.5h)

**Goal:** given a Funda URL → `{price_eur, address, type, size_m2, year_built}`.

### Tasks

1. `backend/funda.py`:
   - `async def fetch_funda(url: str) -> str` — `httpx.AsyncClient` with a real browser `User-Agent`, `Accept-Language: nl-NL`, HTTP/2. 5s timeout.
   - `async def parse_funda(html: str) -> dict` — two paths in order:
     1. **JSON-LD first:** `<script type="application/ld+json">` contains `offers.price`, `address`, `floorSize`. Fast, free, no tokens.
     2. **LLM fallback:** feed first ~8k tokens of body-only HTML to Claude with the Funda prompt from `prompts.py`. Validate JSON shape.
   - `def regex_price_fallback(html: str) -> int | None` — `€\s?([\d.]+)` last resort.
2. `POST /onboard/parse-funda` body `{url: str}` → returns the dict.

### Pitfalls

- **Bot protection:** Funda may 403 a server IP. Tier list: (1) proper headers, (2) `httpx[http2]`, (3) **demo escape hatch**: cache HTML for demo URLs to `backend/mocks/funda_listings/` and read from disk when `FUNDA_MODE=fixture`. Manual price entry is already in-scope per CLAUDE.md, so fixture fallback is fine.
- **Only price + address are required.** Size and year are nice-to-have. The projection math only needs `price_eur`.

---

## Phase 5 — bunq client (1.5h)

**Goal:** uniform interface for transactions, buckets, money moves. Fixture mode default.

### Tasks

1. `backend/bunq_client.py`:
   - `class BunqClient(Protocol)`: `get_transactions`, `get_buckets`, `move_money`, `create_bucket`.
   - `class FixtureBunqClient` — reads `mocks/transactions.json` + `mocks/buckets.json`, mutates an in-memory copy for writes, returns deterministic fake `ExecutionRef`s.
   - `class RealBunqClient` — stub with `raise NotImplementedError`. Implement in Phase 11 if time.
   - Factory `def get_bunq_client() -> BunqClient` based on `BUNQ_MODE` env var.
2. `backend/mocks/transactions.json` — **hand-craft Tim's 6 months.** Monthly salary deposit, rent, groceries, leisure. Numbers must reconcile to €34k savings. The projection runs on these.
3. `backend/mocks/buckets.json` — at least: checking account, "Buffer" (~€3k), "Savings/House" (~€34k).

### Pitfalls

- **Real bunq OAuth is non-trivial.** Multi-step handshake (installation → device server → session) before first API call. Budget 3+ hours. If behind at the 12h checkpoint, stay on fixture mode.
- **Token encryption:** if you go live, store tokens encrypted (Fernet with key from env). Never log tokens. Add `__repr__` that redacts the value.
- **Idempotency on writes:** 60s in-memory dedupe keyed by `tool_use_id`. Prevents double-execute on retry.

---

## Phase 6 — Projection math (1h, parallelizable with Phase 5)

**Goal:** pure function `compute_projection(profile, transactions, buckets) -> Projection`. Tested.

### Tasks

1. `backend/projection.py`:
   - `NIBUD_2026 = {...}` — **look up the actual multiplier at start of build.** Do not guess.
   - `def deposit_target(price_eur: float) -> float` — typically 10% own funds + 4% kosten koper. Verify the current rule.
   - `def monthly_savings_rate(transactions, window_days=180) -> float` — net inflows minus outflows over window, divided by months. Clip to 5–95th percentile of monthly deltas to trim outliers.
   - `def headroom_range(gross_monthly_eur: float) -> tuple[int, int]` — Nibud multiplier ± ~8% band. **Never a single figure** — the range framing is regulatory.
   - `def compute_projection(...) -> Projection` — assembles the dict matching `data-model.md`.
2. `backend/tests/test_projection.py` — Tim case: €34k saved, €425k target → expect ~€21k gap, ~14 months, headroom range bracketing €425k. Pin these numbers in the test.

### Pitfalls

- **Wft language in key names:** use `headroom_range_eur` (a range), never `max_borrow_eur` (a definite claim).
- **No scenario sliders.** CLAUDE.md cuts them explicitly.
- **Time zones:** always `datetime.now(tz=UTC)`. Never naive datetimes.

---

## Phase 7 — Onboarding endpoint (1h)

**Goal:** `POST /onboard` stitches everything together and returns a bootstrapped session id.

### Tasks

1. `POST /onboard` body: `{payslip: {...}, funda_url: str, bunq_oauth_code?: str}`
   - The payslip and Funda data are already extracted by separate prior calls; this endpoint commits them.
2. Sequence:
   1. `funda = await parse_funda(funda_url)` (uses fixture if `FUNDA_MODE=fixture`)
   2. `bunq_snapshot = bunq_client.get_transactions() + get_buckets()` — in parallel
   3. `projection = compute_projection(payslip, funda, transactions, buckets)`
   4. `storage.upsert_profile(Profile(...))`
   5. `session = storage.create_session(user_id)`
   6. Append a hidden synthetic turn: `Turn(kind="user_message", content="<INTERNAL: profile bootstrapped>", hidden=True)`
   7. Return `{session_id, profile, projection}`
3. **Don't open the SSE stream from inside `/onboard`.** Frontend navigates to `/chat` then immediately POSTs `{type: "system_bootstrap"}` to trigger the first agent reply.

### Pitfalls

- **No transactions needed for a failed onboard.** If any step fails, the user re-submits. Not worth making this transactional.
- **`hidden: bool` on `Turn` model.** `list_turns` defaults to `include_hidden=False`. Chat history endpoint uses the default.

---

## Phase 8 — Chat agent + SSE (3–4h) ← THE MAIN EVENT

**Goal:** `POST /chat/sessions/{id}/turns` returns a correct SSE stream implementing `agent-loop.md` §3.

### Tasks

1. `backend/agent/system_prompt.py`:
   - `def build_system_prompt(user_id: str, storage: Storage) -> str`
   - Loads profile, prepends the canonical prompt from `prompts.py` (imported, never copied), adds profile snapshot + Nibud norms + tool reminder.

2. `backend/agent/tools.py`:
   - `TOOL_SCHEMAS` — exactly as in `agent-loop.md` §4.
   - `READ_TOOLS = {"get_bunq_transactions", "get_bunq_buckets", "get_funda_property", "compute_projection"}`
   - `def is_read_only(name: str) -> bool: return not name.startswith("propose_")`
   - Also assert `name in READ_TOOLS` for read tools; reject anything unknown.
   - `async def execute_read_tool(name, params, ctx) -> dict` — dispatches to clients. **Truncate large results to ≤2k tokens before returning to the model** (summarize transaction aggregates).

3. `backend/agent/runner.py` — `async def run_turn(session_id, inbound_event, storage, sse_emit)`:
   - Persist inbound event **before** calling the model.
   - `tool_approval` branch: load PendingTool → execute side-effect → persist `tool_result` turn → clear pending → fall through to model call with result in history.
   - Model stream loop:
     - `text_delta` → `sse_emit("delta", {"text": chunk})`
     - `tool_use` + read-only → `sse_emit("tool_call")` + execute + `sse_emit("tool_result")` + append to history + **break inner loop, restart model call**
     - `tool_use` + `propose_*` → persist `PendingTool` + `sse_emit("tool_proposal")` + `sse_emit("done", {"reason": "awaiting_approval"})` + return
     - End-of-stream, no pending tool → `sse_emit("done", {"reason": "complete"})` + return
   - **One pending approval per session** — assert none exists before persisting a new one.

4. `backend/routes/chat.py`:
   - `GET /chat/sessions` — list user sessions, most recent first, limit 20.
   - `GET /chat/sessions/{id}` — session metadata + non-hidden turns.
   - `POST /chat/sessions/{id}/turns` — `EventSourceResponse` from `sse_starlette`. Headers: `X-Accel-Buffering: no`, `Cache-Control: no-store`. Use `ping=15` for heartbeat.

### SSE event format (must match `agent-loop.md` §2 exactly)

```
event: delta
data: {"text": "..."}

event: tool_call
data: {"tool_use_id": "tu_01...", "name": "get_bunq_transactions", "params": {...}, "kind": "read"}

event: tool_result
data: {"tool_use_id": "tu_01...", "ok": true, "summary": "..."}

event: tool_proposal
data: {"tool_use_id": "tu_02...", "name": "propose_move_money", "params": {...}, "summary": "...", "risk_level": "low", "rationale": "..."}

event: done
data: {"reason": "complete"}
```

### Pitfalls

- **Anthropic streaming is event-driven, not chunk-driven.** Use `client.messages.stream(...)` as an async context manager and iterate `async for event in stream`. Events: `MessageStartEvent`, `ContentBlockStartEvent`, `ContentBlockDeltaEvent` (with `delta.text` or `delta.partial_json`), `ContentBlockStopEvent`, `MessageStopEvent`. Tool inputs arrive as streamed JSON deltas you must accumulate then `json.loads`.
- **Tool result format in history:** must be a `user` role message with `[{"type": "tool_result", "tool_use_id": ..., "content": "..."}]`. The assistant's `tool_use` block must be in history paired with that exact `id`. Get this wrong and the model will error or hallucinate.
- **Restarting after a tool result is not free** — each restart is a new `messages.create` call. Keep history short; truncate tool results aggressively.
- **SSE gotcha #1:** every event ends with `\n\n`. Use `sse_starlette` — don't handroll SSE.
- **SSE gotcha #2:** browsers cap 6 parallel SSE connections per origin. Don't open auxiliary streams.
- **Malformed tool JSON:** wrap accumulated `partial_json` in try/except; on failure send a synthetic `tool_result` saying "invalid JSON, please retry" and let the model recover.
- **Disconnect handling:** wrap `run_turn` in try/finally. On disconnect, flush any buffered assistant text as a `Turn` so history has no holes.
- **Idempotency key:** accept `client_idempotency_key` in request body; dedupe against last 60s of turns for that key.

---

## Phase 9 — Approval execution wiring (45 min)

**Goal:** `tool_approval` flow executes the bunq side-effect correctly.

### Tasks

```python
# In run_turn, approval branch:
pending = storage.get_pending_tool(session_id, evt.tool_use_id)
if not pending:
    sse_emit("error", {"message": "No matching pending action."}); return

if evt.decision == "approve":
    # Re-validate overrides against the tool's input schema before executing.
    params = {**pending.params, **(evt.overrides or {})}
    try:
        ref = await bunq_client.execute(pending.tool_name, params, user_id=user_id)
        result_for_model = {"ok": True, "execution_ref": ref}
    except BunqError as e:
        result_for_model = {"ok": False, "error": str(e)}
else:
    result_for_model = {"declined_by_user": True, "feedback": evt.feedback}

storage.append_turn(session_id, Turn(kind="tool_result", tool_use_id=evt.tool_use_id, result=result_for_model))
storage.clear_pending_tool(session_id, evt.tool_use_id)
# Fall through to model loop with tool_result in history.
```

### Pitfalls

- **Always clear pending** — success, failure, or denial. Prevents double-execute on retry.
- **`overrides` is user-supplied.** Re-validate against the tool schema before executing. Never trust the frontend.
- Don't call the model again just to summarize the result — it will see the `tool_result` in history naturally on the next loop iteration.

---

## Phase 10 — End-to-end smoke (1h, everyone together)

**Goal:** full flow driven with `curl`, producing correct SSE output.

### Tasks

1. Write `scripts/smoke.sh`:
   ```bash
   # 1. Upload payslip
   curl -s -X POST http://localhost:8000/onboard/upload-payslip \
     -F "file=@demo/payslip_tim.jpg" | jq

   # 2. Parse Funda
   curl -s -X POST http://localhost:8000/onboard/parse-funda \
     -H "Content-Type: application/json" \
     -d '{"url":"https://www.funda.nl/..."}' | jq

   # 3. Onboard
   SESSION_ID=$(curl -s -X POST http://localhost:8000/onboard \
     -H "Authorization: Bearer demo" \
     -H "Content-Type: application/json" \
     -d '{"payslip":{...},"funda_url":"..."}' | jq -r .session_id)

   # 4. First turn (streaming — note -N)
   curl -N -X POST http://localhost:8000/chat/sessions/$SESSION_ID/turns \
     -H "Authorization: Bearer demo" \
     -H "Content-Type: application/json" \
     -H "Accept: text/event-stream" \
     -d '{"type":"user_message","content":"How am I doing?"}'

   # 5. Trigger a write proposal
   curl -N -X POST http://localhost:8000/chat/sessions/$SESSION_ID/turns \
     -H "Authorization: Bearer demo" \
     -H "Content-Type: application/json" \
     -H "Accept: text/event-stream" \
     -d '{"type":"user_message","content":"Move €200 from buffer to house"}'

   # 6. Approve (substitute real tool_use_id from previous response)
   curl -N -X POST http://localhost:8000/chat/sessions/$SESSION_ID/turns \
     -H "Authorization: Bearer demo" \
     -H "Content-Type: application/json" \
     -H "Accept: text/event-stream" \
     -d '{"type":"tool_approval","tool_use_id":"tu_01...","decision":"approve"}'
   ```

2. Run the smoke ≥5 times. Any flaky path → tighten the system prompt or reduce model temperature before continuing.
3. **Add structured logging** at every model call boundary: `model_id`, `input_tokens`, `output_tokens`, `tool_uses`, `latency_ms`. Print to stdout.

### Pitfalls

- **Pre-warm the model on server startup** with a dummy call to avoid cold-start latency on the first demo call.
- **`curl -N` is mandatory.** Without it, curl buffers the response and you'll think SSE is broken.

---

## Phase 11 (only if time) — AWS swap-ins

Do in this order, stop when out of time. Each is ~1–2h.

| Step | What changes | Nothing else changes |
|---|---|---|
| 11.1 DynamoDB | Implement `dynamo_store.py` against `Storage` Protocol; set `STORAGE_BACKEND=dynamo` | All routes, agent loop, tools |
| 11.2 S3 + presigned upload | Replace `POST /onboard/upload-payslip` with `/upload-url` + direct S3 PUT; backend reads from S3 | Extractor logic |
| ~~11.3 Bedrock~~ | ~~Done in Phase 2.~~ `AsyncAnthropicBedrock` is the default client. | — |
| 11.4 Cognito | Replace `Bearer demo` shortcut with `python-jose` + Cognito JWKS | Everything else |
| 11.5 Deploy | Containerize, push to ECR, App Runner | All of the above |

**Pitfall:** every swap is a regression risk. Lock the local build, branch for each swap, only merge when smoke passes.

---

## Cross-cutting non-negotiables

- **Wft language audit before demo.** Grep for `you should`, `you can afford`, `I recommend`, `the best`, `you qualify`. Zero hits required.
- **Disclaimer string** lives in one constant in `backend/prompts.py:DISCLAIMER`. Returned by `GET /chat/sessions/{id}` so the frontend has one source of truth.
- **`prompts.py` is the contract.** Do not duplicate prompt text anywhere else. Do not touch it without sign-off.
- **Demo escape hatches for everything network-bound:**
  - `BUNQ_MODE=fixture`
  - `FUNDA_MODE=fixture`
  - `DEMO_REPLAY=1` for pre-cached Bedrock responses if conference WiFi flakes

---

## Parallelization guide (2–3 people)

After Phases 0–1 are merged, these tracks are fully independent:

| Person A — agent track | Person B — data track | Person C — infra (optional) |
|---|---|---|
| Phase 2 — Anthropic client | Phase 3 — Payslip extractor | Phase 11.1 — DynamoDB |
| Phase 8 — Agent + SSE | Phase 4 — Funda parser | Phase 11.3 — Bedrock |
| Phase 9 — Approval wiring | Phase 5 — bunq fixture | Phase 11.5 — Deploy |
| | Phase 6 — Projection math | |
| | Phase 7 — Onboarding endpoint | |

Phase 10 (smoke) is everyone, last hour before the demo.

---

## See also

- `wiki/architecture.md` — system components and AWS layout
- `wiki/agent-loop.md` — SSE event schema, tool-use loop pseudocode, failure modes
- `wiki/data-model.md` — DynamoDB item shapes, access patterns, S3 layout
- `CLAUDE.md` — product framing, regulatory guardrails, canonical prompts, build order