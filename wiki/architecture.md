# bunq Nest — Architecture

Target: hackathon MVP, AWS-centric path. Read alongside `CLAUDE.md` (product framing, regulatory guardrails) and the sibling docs in this folder.

> Status: this is the architecture we're *building toward in the 24h window*. Anything marked **[risk]** is a spot to fall back to a simpler local path if we run out of time.

---

## 1. What the system does

bunq Nest has two surfaces:

1. **Onboarding form** — shown once per user, after first login. Captures a payslip photo + a Funda URL, extracts the data, stitches it together with bunq snapshot data, persists a profile, and bootstraps the first chat turn.
2. **Chat agent** — the ongoing surface. The user comes back into a conversation that already knows their profile, their bunq state, and their goal. The agent answers questions, proposes actions (with approval), and pulls fresh data from bunq on demand.

The form is throwaway; the chat is the product.

---

## 2. Components (10,000 ft)

```
┌─────────────────┐         ┌──────────────────────────────────────────────┐
│   React + Vite  │         │                Backend (FastAPI)             │
│   (browser)     │  HTTPS  │                                              │
│                 │ ───────▶│  /auth/*    Cognito-issued JWT verify         │
│  - Onboarding   │         │  /onboard   one-shot bootstrap                │
│  - Chat (SSE)   │ ◀─SSE── │  /chat/*    turns, streaming, approvals       │
│                 │         │  /bunq/*    OAuth callback + proxy            │
└─────────────────┘         └────────────┬─────────────────────────────────┘
                                          │
        ┌─────────────────────────────────┼──────────────────────────────────┐
        ▼                                 ▼                                  ▼
┌─────────────────┐               ┌──────────────────┐              ┌─────────────────┐
│   S3            │               │   DynamoDB       │              │  Bedrock        │
│  payslip-imgs/  │               │  Users           │              │  (Anthropic)    │
│  + presigned    │               │  Sessions        │              │  - Claude vision│
│    PUT URLs     │               │  Turns           │              │  - Sonnet 4.6   │
└────────┬────────┘               │  ToolRuns        │              │    chat agent   │
         │ ObjectCreated          │  BunqTokens      │              └─────────────────┘
         ▼                        └──────────────────┘
┌─────────────────┐                                                  ┌─────────────────┐
│  Lambda         │── Bedrock VLM ─▶ extracted JSON ──▶ DynamoDB    │  bunq Public API│
│  payslip-extract│                                                  │  + Funda fetch  │
└─────────────────┘                                                  └─────────────────┘
```

**Why this shape:**

- **AWS-only data plane.** All user data (images, profile, chat history, tokens) lives in our AWS account. Bedrock keeps inference inside AWS too. One IAM perimeter, one audit story, one region (`eu-central-1` recommended for EU residency).
- **Lambda for image processing only.** The chat path stays inside FastAPI because per-turn streaming + agent-loop control flow is awkward to split across Lambdas. Image extraction is one-shot, async, fits Lambda perfectly.
- **DynamoDB as the single primary store.** AWS-native, no connection pool to manage from Lambda, scales to zero, single-table design covers users + sessions + turns + tool runs. See `data-model.md`.
- **SSE, not WebSockets.** The agent-to-user data flow is one-way streaming text. SSE is a single HTTP response, works through ALB/CloudFront without sticky-session config, and degrades gracefully. User input is plain `POST`. WebSockets buy us nothing here and cost us complexity. See `agent-loop.md` for the turn lifecycle.

---

## 3. End-to-end flow — first session

```
[User opens app for the first time]
       │
       ▼
1. Login (Cognito hosted UI) ──▶ JWT in browser
       │
       ▼
2. Backend sees user.onboarded == false ──▶ redirect /onboard
       │
       ▼
3. Browser asks /onboard/upload-url ──▶ presigned S3 PUT URL
       │
       ▼
4. Browser uploads payslip directly to s3://payslip-imgs/{user}/{uuid}.jpg
       │      and POSTs /onboard with { s3_key, funda_url, bunq_oauth_code }
       ▼
5. Backend:
   ├── completes bunq OAuth code → access/refresh token, encrypts, stores
   ├── triggers payslip-extract Lambda (sync invoke, ~3-5s) ──▶ Bedrock vision
   │       returns { gross_monthly_eur, net_monthly_eur, employer_name, ... }
   ├── fetches Funda URL ──▶ Sonnet 4.6 extracts price/address/size
   ├── pulls bunq snapshot: monetary-accounts, last 6mo transactions, buckets
   └── writes Users#profile, creates Session#1, computes initial projection
       │
       ▼
6. Backend opens SSE on /chat/sessions/{id}/stream with synthetic context turn.
   Agent's first reply streams: "Hi Tim — I see €34k saved, target €55k.
   At your current rate, you're ~14 months out. Want me to..."
       │
       ▼
7. User stays in chat from here on.
```

Subsequent logins skip steps 3–5; the user lands directly in `/chat` with the most recent session resumed (or a fresh session bootstrapped from the persisted profile + a fresh bunq snapshot).

---

## 4. Image pipeline (AWS, payslip)

```
Browser ──PUT presigned URL──▶ S3: payslip-imgs/{user_id}/{img_id}.jpg
                                  │
                                  │ s3:ObjectCreated:Put  (or sync invoke from API)
                                  ▼
                            Lambda: payslip-extract
                                  │
                                  │ bedrock:InvokeModel
                                  │   modelId: anthropic.claude-3-5-sonnet-...
                                  │   (or Sonnet 4.6 vision once available on Bedrock)
                                  ▼
                            { gross_monthly_eur, net_monthly_eur,
                              employer_name, pay_period, confidence }
                                  │
                                  ▼
                  DynamoDB: Users#{user_id} attribute payslip = {...}
                                  │
                                  ▼
                       (optional) SNS publish "profile.updated"
```

**Decisions and trade-offs:**

| Decision | Choice | Why | Trade-off |
|---|---|---|---|
| Trigger | **Sync invoke from API**, not S3 event | The onboarding flow needs the result inline to render the dashboard. S3 events are eventually consistent and add a polling step. | Lambda invocation timeout matters — must complete in under 30s API-Gateway window. Bedrock VLM is well within budget (~3-5s for a payslip). |
| Model | Anthropic Claude vision via Bedrock | Same model family as the chat agent, EU-region inference, IAM-controlled. | Sonnet 4.6 vision availability on Bedrock may lag the direct Anthropic API. **[risk]** Confirm at build time; fall back to whichever Anthropic vision model is current on Bedrock `eu-central-1`. |
| Storage | S3 with bucket-default SSE-KMS | Encryption at rest by default. Presigned PUT URLs avoid streaming the image through our backend. | Browser uploads bypass our backend, so we can't strip EXIF / size-check before storage. Mitigation: enforce `Content-Length` and `Content-Type` constraints in the presigned URL signature; run a tiny normalization step inside the Lambda (resize/strip EXIF) before invoking Bedrock. |
| Retention | S3 lifecycle: delete original after 30d; keep extracted JSON | The image is sensitive PII; the extracted numbers are what we actually need. | If a user disputes the extraction we lose the original after 30d. Acceptable for an MVP; document in the privacy notice. |
| Failure | Lambda returns `confidence: "low"` if any field is null | The frontend prompts for manual entry. Same UX as the existing manual-price fallback for Funda. | None — this is the right behavior. |

---

## 5. Chat agent (Sonnet 4.6 on Bedrock)

The agent is the heart of the product. Full lifecycle, streaming protocol, and the human-in-the-loop pattern for tool calls is in `agent-loop.md`. Summary:

- **Each user-visible turn is one HTTP `POST /chat/sessions/{id}/turns`** that returns an SSE stream.
- The agent loop runs server-side. Read-only tools (`get_bunq_transactions`, `get_funda_property`, `compute_projection`) auto-execute inside the same stream — the user just sees text deltas. Write tools (`move_money_between_buckets`, `create_savings_bucket`) emit a structured `tool_proposal` event, end the stream, and wait for explicit user approval before executing.
- Conversation state (messages, pending tool calls, approval decisions) lives in DynamoDB. The agent loop is fully resumable — a user closing the tab mid-approval still finds the proposal waiting when they return.
- The agent **never** recommends mortgage products, lenders, or rate types. The system prompt enforces this and is the same Wft-safe coaching prompt already canonical in `CLAUDE.md`.

Tools the agent has (initial set):

| Tool | Type | Effect |
|---|---|---|
| `get_bunq_transactions(window)` | read | Pulls recent transactions for projection refresh |
| `get_bunq_buckets()` | read | Lists Savings buckets and balances |
| `get_funda_property(url)` | read | Re-fetches the target property |
| `compute_projection()` | read | Re-runs the deterministic Nibud math over current state |
| `propose_move_money(from, to, amount, reason)` | **write — needs approval** | Moves money between bunq buckets |
| `propose_create_bucket(name, target)` | **write — needs approval** | Creates a new bunq Savings bucket |
| `propose_handoff_advisor()` | **write — needs approval** | Triggers the advisor handoff CTA flow |

Read tools execute eagerly. Write tools always go through the approval lane. The split is enforced by tool naming (`propose_*`) and a hard check in the agent loop runner.

---

## 6. Auth and bunq OAuth

| Concern | Approach |
|---|---|
| User sign-in to bunq Nest | **Amazon Cognito** user pool with the hosted UI (email + password; social later). Issues a JWT access token, verified by FastAPI on every request. |
| Linking bunq | Standard OAuth 2.0 authorization-code flow against bunq's API. The `/bunq/oauth/callback` exchanges the code for an access + refresh token, encrypts them with KMS (`alias/bunq-tokens`), and stores in DynamoDB under `BunqTokens#{user_id}`. |
| Token use | A `BunqClient` helper in the backend loads the encrypted token, decrypts on demand, signs API calls. Refresh tokens are used silently when the access token is near expiry. |
| Scopes | Read transactions + buckets for the read tools. Write scope (move money, create bucket) only requested when the user first triggers an action that needs it — incremental consent. |
| Token rotation | Refresh tokens stored encrypted; rotated on every refresh; old version overwritten. No plaintext token ever leaves the backend. |
| Session timeout | Cognito JWT lifetime: 1h access / 30d refresh. bunq tokens live independently; if bunq revokes, the next API call surfaces a re-auth prompt in chat. |

**[risk]** Real bunq OAuth in 24h is non-trivial. If we're behind at the 12h mark, fall back to a stubbed `BunqClient` that reads from a fixture JSON file — the rest of the architecture stays identical.

---

## 7. Storage layout — at a glance

Full schema in `data-model.md`. TL;DR:

- **S3** — `payslip-imgs/{user_id}/{img_id}.jpg`, server-side encryption, 30d lifecycle.
- **DynamoDB single table `bunq-nest-main`**:
  - `PK = USER#{user_id}`, `SK = PROFILE` — extracted payslip, target property, derived projection, `onboarded_at`.
  - `PK = USER#{user_id}`, `SK = SESSION#{session_id}` — session metadata.
  - `PK = SESSION#{session_id}`, `SK = TURN#{epoch_ms}#{turn_id}` — append-only chat turns (user message, agent message, tool call, tool result, approval decision).
  - `PK = USER#{user_id}`, `SK = BUNQ_TOKEN` — encrypted token blob, KMS key id, expires_at.
  - `PK = SESSION#{session_id}`, `SK = PENDING_TOOL#{tool_use_id}` — durable pending approvals.

GSI1 (`user_id` → `last_active_at`) lets us list sessions per user.

---

## 8. Deployment shape

| Layer | Service | Notes |
|---|---|---|
| Frontend | Vercel | Already in CLAUDE.md. No change. |
| Backend API | FastAPI on **AWS App Runner** (or ECS Fargate) | App Runner is the lowest-effort path: one container, public HTTPS, IAM role for AWS calls. SSE works through it without extra config. |
| Image Lambda | AWS Lambda + S3 trigger (or sync invoke) | `eu-central-1`, 1GB memory, 30s timeout. |
| Inference | Amazon Bedrock | `eu-central-1` for residency. Models pinned by id. |
| Auth | Amazon Cognito | Hosted UI, one user pool. |
| Data | DynamoDB on-demand, S3, KMS | All in one region. |
| Logs/metrics | CloudWatch Logs + a single dashboard | Bedrock token usage, Lambda duration, agent turn p95. |

---

## 9. What we're explicitly *not* doing

- **No vector store / RAG.** The chat agent's context is small and structured (profile + recent transactions + Nibud norms). No need.
- **No background workers / queues.** Every turn is interactive. Approvals are durable rows, not jobs.
- **No multi-region.** EU only. One region.
- **No fine-tuning, no system-of-record swap, no microservices.** One backend service, one Lambda, one chat loop.

---

## 10. What we'd revisit if this scaled past the demo

| Pain | When it bites | Likely move |
|---|---|---|
| FastAPI on a single App Runner container holds long SSE streams | A few hundred concurrent chats | Move chat to ECS with horizontal scaling, or to a Lambda + API Gateway WebSocket if streams get longer-lived |
| DynamoDB hot partition on a chatty user's session | A power user sends thousands of turns | Add a write-sharding suffix on `SESSION#{id}#{shard}` |
| Refreshing bunq snapshot on every chat open | Many DAU | Stream bunq data via webhooks into our store, serve from cache |
| Single region | Non-EU expansion | Add a second region with cross-region replication on DynamoDB and S3 |
| Audit / compliance over agent actions | Real money moves at scale | Persist a tamper-evident log of every approved tool call (separate WORM bucket) |

---

## 11. Frontend–backend contracts (frozen at hour 0)

These TypeScript types are the **single source of truth** for every byte that crosses the frontend/backend boundary. They live in `frontend/src/api/types.ts`. A and B must not change a field name, add a required field, or drop a field without updating this section first — doing so silently breaks the frontend parser or the mock fixtures.

### 11.1 SSE events — backend → frontend (A owns)

Every `event:` line the backend emits maps to exactly one of these. The frontend parser rejects anything not in this union.

```ts
type SseEvent =
  | { event: 'delta';         data: { text: string } }
  | { event: 'tool_call';     data: { tool_use_id: string; name: ToolName;
                                       params: object; kind: 'read' } }
  | { event: 'tool_result';   data: { tool_use_id: string; ok: boolean;
                                       summary?: string; error?: string } }
  | { event: 'tool_proposal'; data: ToolProposal }
  | { event: 'done';          data: { reason: 'complete' | 'awaiting_approval' } }
  | { event: 'error';         data: { message: string; retryable: boolean } };

type ToolName =
  | 'get_bunq_transactions'
  | 'get_bunq_buckets'
  | 'get_funda_property'
  | 'compute_projection'
  | 'propose_move_money'
  | 'propose_create_bucket'
  | 'propose_handoff_advisor';

type ToolProposal = {
  tool_use_id: string;
  name: 'propose_move_money' | 'propose_create_bucket' | 'propose_handoff_advisor';
  params: ProposeMoveMoneyParams | ProposeCreateBucketParams | {};
  summary: string;      // human-readable one-liner — rendered in the approval card
  rationale: string;    // 1–2 sentence explanation shown below the summary
  risk_level: 'low' | 'medium' | 'high';
};

type ProposeMoveMoneyParams = {
  from_bucket_id: string;
  from_bucket_name: string;   // ← A must include this; card cannot render without it
  to_bucket_id: string;
  to_bucket_name: string;     // ← same
  amount_eur: number;
  reason: string;
};

type ProposeCreateBucketParams = {
  name: string;
  target_eur?: number;
  reason: string;
};
```

**Note on bucket names:** the approval card renders `from_bucket_name → to_bucket_name` directly. A must embed the human-readable name in the proposal params — the frontend will not make a secondary fetch to resolve bucket IDs.

### 11.2 Turn request bodies — frontend → backend (A owns)

```ts
type TurnRequest =
  | { type: 'user_message';
      content: string;
      idempotency_key: string; }        // UUIDv4, generated client-side; dedupe window = 60s
  | { type: 'tool_approval';
      tool_use_id: string;              // from ToolProposal.tool_use_id
      decision: 'approve' | 'deny';
      overrides?: { amount_eur?: number };  // editable fields only; currently amount_eur for propose_move_money
      feedback?: string;                // optional, shown to user on deny
      idempotency_key: string; };
```

**Note on editable fields:** the only field the frontend exposes for user editing in the approval card is `amount_eur` on `propose_move_money`. If A adds editable fields to other proposal types, update `overrides` here and in `ApprovalCard.tsx`.

### 11.3 Onboarding endpoints — frontend → backend (B owns)

**Status: shapes proposed by C, need B's sign-off at hour-0 huddle.**

```ts
// POST /onboard/upload-url  →  UploadUrlResponse
type UploadUrlResponse = {
  upload_url: string;       // presigned S3 PUT, expires in 5 min
  s3_key: string;           // pass back verbatim in OnboardRequest
  expires_at: number;       // epoch ms — frontend shows a warning if upload is slow
  required_headers: Record<string, string>;  // e.g. { 'Content-Type': 'image/jpeg' }
};

// POST /onboard  →  OnboardResponse
type OnboardRequest = {
  s3_key: string;
  funda_url: string;
  funda_price_override_eur?: number;  // manual fallback if LLM extraction fails
};
// Note: no bunq_oauth_state — the backend uses a static sandbox API key,
// keyed off the (hard-coded) user_id.

type OnboardResponse = {
  session_id: string;       // first session, ready to stream immediately
  profile: ProfileSnapshot; // pre-rendered numbers for the populating animation
};

type ProfileSnapshot = {
  payslip: {
    gross_monthly_eur: number;
    net_monthly_eur: number;
    confidence: 'high' | 'medium' | 'low';
  };
  target: {
    price_eur: number;
    address: string;
  };
  projection: {
    savings_now_eur: number;
    deposit_target_eur: number;
    gap_eur: number;
    monthly_savings_eur: number;
    months_to_goal: number;
    headroom_range_eur: [number, number];
  };
};
```

**Note on `ProfileSnapshot`:** the frontend animates these numbers immediately on `OnboardResponse` receipt, before the agent's first SSE stream arrives. B must populate all fields; `null` values will break the animation.

### 11.4 Open items (resolve at hour-0 huddle, ≤30 min)

| # | Owner | Question | Blocks |
|---|---|---|---|
| 1 | A | Confirm `from_bucket_name` / `to_bucket_name` are included in `propose_move_money` params. | `ApprovalCard.tsx` |
| 2 | B | Sign off on `UploadUrlResponse` and `OnboardRequest` / `OnboardResponse` shapes above. | `PayslipUpload.tsx`, `AuthCallbackRoute.tsx` |
| 3 | A | Does the bootstrap session stream start automatically after `/onboard`, or does the frontend fire an explicit `POST /turns`? | `ChatRoute.tsx` bootstrap logic |
| 4 | B | Confirm both `localhost:5173` and the Vercel production URL are registered as `redirect_uri` for the bunq OAuth app. | `BunqConnect.tsx` |
| 5 | A | Pin the editable-fields allowlist for `overrides` — is `amount_eur` the only one for MVP? | `ApprovalCard.tsx` edit mode |
| 6 | A + B | Who sets `risk_level` on a proposal — the agent or the runner deterministically? Doesn't change the frontend but affects whether `high` can appear in production. | `ApprovalCard.tsx` risk badge |

---

## See also

- `agent-loop.md` — the turn lifecycle, streaming protocol, ask-user vs tool-approval patterns.
- `data-model.md` — DynamoDB single-table design, JSON shapes for turns and tool calls.
- `CLAUDE.md` (project root) — product framing, regulatory guardrails, canonical prompts.
