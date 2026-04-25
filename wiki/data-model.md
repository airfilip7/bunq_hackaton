# Data model

DynamoDB single-table design + S3 layout for bunq Nest. Keep this in lockstep with `architecture.md` and `agent-loop.md`.

---

## 1. Why a single DynamoDB table

- All access is keyed off `user_id` and (sometimes) `session_id`. Both compose naturally into a partition key.
- We only have a handful of entity types (User, Session, Turn, ToolRun, PendingTool). A single-table design keeps the operational surface tiny — one table, one set of IAM, one backup.
- DynamoDB on-demand mode means zero capacity planning for the hackathon.

Table name: `bunq-nest-main`. Region: `eu-central-1`. Encryption: AWS-owned KMS by default.

**Note on bunq credentials:** the demo uses a static sandbox API key per demo user, held in the backend's secret manager (not DynamoDB). A `BUNQ_TOKEN` row would be added in production when real OAuth replaces the sandbox key — out of MVP scope.

---

## 2. Keys and entity layout

| Entity | PK | SK | Notes |
|---|---|---|---|
| User profile | `USER#{user_id}` | `PROFILE` | One row per user. Holds payslip extract, target property, derived projection, `onboarded_at`. |
| Session | `USER#{user_id}` | `SESSION#{session_id}` | One row per chat session. Stores `started_at`, `last_active_at`, `state` (`active` / `closed`). |
| Turn | `SESSION#{session_id}` | `TURN#{ts_ms}#{turn_id}` | Append-only chat history. `ts_ms` first → naturally sortable. |
| Tool run | `SESSION#{session_id}` | `TOOLRUN#{tool_use_id}` | One row per tool invocation. Read-only and write tools both land here. |
| Pending tool (awaiting approval) | `SESSION#{session_id}` | `PENDING_TOOL#{tool_use_id}` | Deleted when approved/denied. Presence = "awaiting approval". |

### GSI1 — sessions by recency

- `GSI1PK = USER#{user_id}`
- `GSI1SK = LAST_ACTIVE#{ts_ms}`
- Lets the chat surface load "most recent session for this user" without scanning.

That's the only secondary index we need.

---

## 3. Item shapes

### User profile

```jsonc
{
  "PK": "USER#u_01HZ...",
  "SK": "PROFILE",
  "user_id": "u_01HZ...",
  "email": "tim@example.com",
  "onboarded_at": 1745625600000,        // null until form completes
  "payslip": {
    "gross_monthly_eur": 4850,
    "net_monthly_eur":   3520,
    "employer_name":     "Acme BV",
    "pay_period":        "2026-03",
    "confidence":        "high",
    "source_s3_key":     "payslip-imgs/u_01HZ.../img_01.jpg",
    "extracted_at":      1745625500000
  },
  "target": {
    "funda_url":   "https://www.funda.nl/...",
    "price_eur":   425000,
    "address":     "Utrecht, NL",
    "type":        "apartment",
    "size_m2":     78,
    "year_built":  1998,
    "fetched_at":  1745625400000
  },
  "projection": {
    "savings_now_eur":     34000,
    "deposit_target_eur":  55000,
    "gap_eur":             21000,
    "monthly_savings_eur": 1450,
    "months_to_goal":      14,
    "headroom_range_eur":  [285000, 320000],
    "computed_at":         1745625600000
  },
  "schema_version": 1
}
```

### Session

```jsonc
{
  "PK": "USER#u_01HZ...",
  "SK": "SESSION#s_01J0...",
  "GSI1PK": "USER#u_01HZ...",
  "GSI1SK": "LAST_ACTIVE#1745625800000",
  "session_id":     "s_01J0...",
  "user_id":        "u_01HZ...",
  "started_at":     1745625600000,
  "last_active_at": 1745625800000,
  "state":          "active"            // "active" | "closed"
}
```

### Turn (append-only, one row per event)

```jsonc
// User message
{
  "PK": "SESSION#s_01J0...",
  "SK": "TURN#1745625610000#t_01J1...",
  "kind": "user_message",
  "content": "How much should I save monthly?",
  "client_idempotency_key": "ik_..."
}

// Assistant text (one row per *complete* assistant message;
// we don't persist every delta — the buffered final text is what survives)
{
  "PK": "SESSION#s_01J0...",
  "SK": "TURN#1745625611000#t_01J2...",
  "kind": "assistant_message",
  "content": "Looking at your last six months...",
  "tool_uses": [ /* anthropic tool_use blocks if any */ ]
}

// Tool result (read or write)
{
  "PK": "SESSION#s_01J0...",
  "SK": "TURN#1745625611200#t_01J3...",
  "kind": "tool_result",
  "tool_use_id": "tu_01...",
  "tool_name":   "get_bunq_transactions",
  "ok":          true,
  "result":      { /* opaque tool output */ }
}

// Approval decision (write tools only)
{
  "PK": "SESSION#s_01J0...",
  "SK": "TURN#1745625620000#t_01J4...",
  "kind": "tool_approval",
  "tool_use_id": "tu_02...",
  "decision":    "approve",       // "approve" | "deny"
  "overrides":   { "amount_eur": 250 },
  "feedback":    null
}
```

### Tool run (one row per tool invocation, materialized for analytics)

```jsonc
{
  "PK": "SESSION#s_01J0...",
  "SK": "TOOLRUN#tu_02...",
  "tool_use_id":   "tu_02...",
  "tool_name":     "propose_move_money",
  "kind":          "write",
  "params":        { "from_bucket_id": "...", "to_bucket_id": "...", "amount_eur": 200 },
  "approved":      true,
  "executed_at":   1745625625000,
  "execution_ok":  true,
  "execution_ref": "bunq:txn_abc123"
}
```

### Pending tool (presence = awaiting user)

```jsonc
{
  "PK": "SESSION#s_01J0...",
  "SK": "PENDING_TOOL#tu_02...",
  "tool_use_id":   "tu_02...",
  "tool_name":     "propose_move_money",
  "params":        { /* original proposal */ },
  "summary":       "Move €200 from Buffer to House — ...",
  "rationale":     "...",
  "risk_level":    "low",
  "proposed_at":   1745625624000
}
```

This row is created when the agent emits a `propose_*` tool call and *deleted* the moment an approval/denial lands. Its presence is the source of truth for "is there a pending action on this session?"

_The `BUNQ_TOKEN` row is **production-only** and not part of the MVP. The demo uses a static sandbox API key in the backend's secret manager._

---

## 4. Common access patterns

| Question | Query |
|---|---|
| Load profile | `GetItem(PK=USER#u, SK=PROFILE)` |
| Most recent session for user | `Query(GSI1PK=USER#u, ScanIndexForward=False, Limit=1)` |
| Conversation history for a session | `Query(PK=SESSION#s, SK begins_with TURN#)` |
| Is there a pending action? | `Query(PK=SESSION#s, SK begins_with PENDING_TOOL#, Limit=1)` |
| All tool runs for a session (analytics) | `Query(PK=SESSION#s, SK begins_with TOOLRUN#)` |

---

## 5. S3 layout

```
s3://bunq-nest-uploads-eu-central-1/
└── payslip-imgs/
    └── {user_id}/
        └── {img_id}.jpg              # original upload
        └── {img_id}.normalized.jpg   # written by Lambda after EXIF-strip + resize
```

- Bucket-default SSE-KMS.
- Lifecycle: delete originals after 30 days; keep `*.normalized.jpg` for 90 days for re-extraction.
- Bucket policy denies `s3:PutObject` without SSE; deny public access at the account level.
- Presigned PUT URLs expire after 5 minutes and are scoped by `Content-Type` + max `Content-Length`.

We do **not** store the extracted JSON in S3 — it goes straight onto the user profile in DynamoDB. The image is the only thing in S3.

---

## 6. Things deliberately not modeled

- **Vector embeddings of past chat.** Not needed; conversation history is linear and short.
- **Per-user analytics tables.** CloudWatch + ad-hoc DynamoDB scans are enough for the demo.
- **Multi-device session merging.** A user with two tabs open is the same session via `session_id` — the idempotency key on `POST /turns` handles dedupe.
- **Soft deletes / GDPR right-to-erasure tooling.** Out of MVP scope; documented as a follow-up.

---

## 7. What we'd revisit at scale

| Pain | Move |
|---|---|
| Hot session partition under heavy chat load | Add a numeric shard suffix to `SESSION#{id}#{shard}` and route writes by hash |
| Need free-text search over chat history | Stream Turns into OpenSearch via DynamoDB Streams |
| Need transactional read+write across tool execution + turn append | DynamoDB transactions (already supported, just not used in MVP — explicit choice for code simplicity) |
| Token blob + profile in the same partition (post-OAuth migration) is a privacy footgun | Move `BUNQ_TOKEN` to a separate, more tightly-scoped table |
