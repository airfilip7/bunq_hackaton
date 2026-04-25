# bunq Nest — Frontend & Onboarding Build Plan

> Branch: `feat/chat-agent`. This plan is written from **Person C's seat** (frontend + onboarding glue). For the agent runner (A) and tools/data plane (B), see the wiki.

---

## 1. Scope (what C ships)

Three deliverables. Priority order is also build order.

1. **`/chat`** — the SSE-streamed chat surface. Renders deltas, tool indicators, approval cards. Owns the input-box state machine across `complete | awaiting_user | awaiting_approval`.
2. **`/onboard`** — the one-time form. Payslip upload, Funda URL, bunq OAuth redirect, the "populating" moment that ends with the first agent message streaming in.
3. **Shell** — Cognito hosted-UI integration, dark theme, bunq teal/yellow accents, Wft disclaimer, greyed handoff CTA.

Out of scope for C: any backend code, the agent loop, tool implementations, payslip Lambda, DynamoDB, bunq API calls. C only talks to A's HTTP endpoints.

---

## 2. Stack (locked)

| Layer | Choice | Why |
|---|---|---|
| Framework | React 18 + Vite + TypeScript | Per CLAUDE.md |
| UI | **shadcn/ui** + Tailwind | Locked. Card, Button, Dialog, Input, Skeleton get used heavily. |
| Routing | React Router v6 | Two routes only (`/onboard`, `/chat`) |
| State | React Query (server state) + Zustand (chat session state) | Avoid Redux; chat state is genuinely client-side. |
| Auth | **Cognito Hosted UI** (full redirect) | Saves ~4h vs custom screens. AWS Amplify Auth or `oidc-client-ts` to handle the JWT lifecycle. |
| Mocking | **MSW** (Mock Service Worker) | In-browser, dev + demo fallback. The unblocker. |
| SSE | `fetch` + `ReadableStream` reader | `EventSource` can't POST. ~40 LOC custom. |
| Forms | React Hook Form + Zod | Onboarding form only |
| Animation | Framer Motion | The "populating" moment. Keep narrow. |

---

## 3. Repo layout (under `frontend/`)

```
frontend/
├── index.html
├── vite.config.ts
├── package.json
├── public/
└── src/
    ├── main.tsx
    ├── App.tsx                    # router, providers, theme
    ├── routes/
    │   ├── OnboardRoute.tsx
    │   ├── ChatRoute.tsx
    │   └── AuthCallbackRoute.tsx  # Cognito + bunq redirects land here
    ├── chat/
    │   ├── ChatView.tsx           # main chat container
    │   ├── MessageList.tsx
    │   ├── AssistantMessage.tsx   # streams text, renders tool pills
    │   ├── UserMessage.tsx
    │   ├── ApprovalCard.tsx       # the propose_* card
    │   ├── ToolPill.tsx           # "checking transactions..." inline indicator
    │   ├── Composer.tsx           # input + send + state-machine
    │   ├── useChatStream.ts       # SSE consumer hook
    │   └── chatStore.ts           # Zustand: session, messages, pending tool, stream state
    ├── onboard/
    │   ├── OnboardForm.tsx
    │   ├── PayslipUpload.tsx      # presigned URL flow
    │   ├── FundaInput.tsx
    │   ├── BunqConnect.tsx        # OAuth redirect button
    │   └── PopulatingDashboard.tsx # the magic moment
    ├── shell/
    │   ├── DisclaimerBanner.tsx
    │   ├── HandoffCTA.tsx         # greyed until months_to_goal <= 6
    │   └── ThemeProvider.tsx
    ├── api/
    │   ├── client.ts              # fetch wrapper + JWT injection
    │   ├── chat.ts                # POST /turns, GET /sessions, etc.
    │   ├── onboard.ts             # presigned URL, /onboard
    │   └── types.ts               # shared contracts (mirror of backend types)
    ├── auth/
    │   ├── cognito.ts             # hosted UI redirect helpers
    │   └── useAuth.ts
    └── mocks/                     # MSW
        ├── browser.ts
        ├── handlers.ts
        └── fixtures/
            ├── pure_text.sse
            ├── read_tool_then_text.sse
            ├── proposal_flow.sse
            ├── error_midstream.sse
            └── bootstrap_first_session.sse
```

---

## 4. The contracts (frozen at hour 0)

Single TypeScript file, `src/api/types.ts`, mirrors backend. A signs off, B signs off, then nobody touches it.

### 4.1 SSE events (from `wiki/agent-loop.md §2` — verbatim)

```ts
type SseEvent =
  | { event: 'delta';         data: { text: string } }
  | { event: 'tool_call';     data: { tool_use_id: string; name: ToolName; params: object; kind: 'read' } }
  | { event: 'tool_result';   data: { tool_use_id: string; ok: boolean; summary?: string; error?: string } }
  | { event: 'tool_proposal'; data: ToolProposal }
  | { event: 'done';          data: { reason: 'complete' | 'awaiting_approval' } }
  | { event: 'error';         data: { message: string; retryable: boolean } };

type ToolProposal = {
  tool_use_id: string;
  name: 'propose_move_money' | 'propose_create_bucket' | 'propose_handoff_advisor';
  params: ProposeMoveMoneyParams | ProposeCreateBucketParams | {};
  summary: string;       // human-readable one-liner — render this in the card
  rationale: string;     // 1-2 sentence explanation
  risk_level: 'low' | 'medium' | 'high';
};

type ProposeMoveMoneyParams = {
  from_bucket_id: string; from_bucket_name: string;  // name needed for the card
  to_bucket_id: string;   to_bucket_name: string;
  amount_eur: number;
  reason: string;
};

type ProposeCreateBucketParams = {
  name: string;
  target_eur?: number;
  reason: string;
};
```

> **Chase A about this:** the schemas in `agent-loop.md §4` only have bucket *ids* in the params. The frontend needs *names* to render the card without an extra fetch. Ask A to include `from_bucket_name` / `to_bucket_name` in the proposal params.

### 4.2 Request bodies to `/turns`

```ts
type TurnRequest =
  | { type: 'user_message'; content: string;
      idempotency_key: string; }
  | { type: 'tool_approval'; tool_use_id: string;
      decision: 'approve' | 'deny';
      overrides?: Partial<ProposeMoveMoneyParams | ProposeCreateBucketParams>;
      feedback?: string;
      idempotency_key: string; };
```

### 4.3 Onboarding (chase B about this — not yet pinned)

```ts
// POST /onboard/upload-url
type UploadUrlResponse = {
  upload_url: string;        // presigned S3 PUT
  s3_key: string;            // pass back in /onboard
  expires_at: number;        // epoch ms
  required_headers: Record<string, string>;  // Content-Type etc.
};

// POST /onboard
type OnboardRequest = {
  s3_key: string;
  funda_url: string;
  funda_price_override_eur?: number;  // manual fallback
  bunq_oauth_state: string;           // returned from /bunq/oauth/callback
};

type OnboardResponse = {
  session_id: string;        // first session, ready to stream
  profile: ProfileSnapshot;  // for instant skeleton-fill
};

type ProfileSnapshot = {
  payslip:    { gross_monthly_eur: number; net_monthly_eur: number; confidence: 'high'|'medium'|'low' };
  target:     { price_eur: number; address: string };
  projection: { savings_now_eur: number; deposit_target_eur: number; gap_eur: number;
                monthly_savings_eur: number; months_to_goal: number;
                headroom_range_eur: [number, number] };
};
```

---

## 5. The MSW unblocker (do this first)

Hour 1 deliverable. From this moment, C never waits on A or B.

```ts
// src/mocks/handlers.ts
import { http, HttpResponse } from 'msw';
import proposalFlow from './fixtures/proposal_flow.sse?raw';
import readTool     from './fixtures/read_tool_then_text.sse?raw';
import bootstrap    from './fixtures/bootstrap_first_session.sse?raw';

let scenario: 'pure_text' | 'read_tool' | 'proposal' = 'proposal';

export const handlers = [
  http.post('/chat/sessions/:id/turns', async ({ request }) => {
    const body = await request.json();
    const fixture = pickFixture(scenario, body);
    return new HttpResponse(streamFixture(fixture, /* delayMs */ 30), {
      headers: {
        'Content-Type': 'text/event-stream',
        'X-Accel-Buffering': 'no',
      }
    });
  }),
  http.post('/onboard/upload-url', () => HttpResponse.json({
    upload_url: 'http://localhost:3000/__mock_s3_put',
    s3_key: 'mock-key',
    expires_at: Date.now() + 300_000,
    required_headers: { 'Content-Type': 'image/jpeg' }
  })),
  http.put('http://localhost:3000/__mock_s3_put', () => new HttpResponse(null, { status: 200 })),
  http.post('/onboard', async () => {
    await sleep(2500); // simulate Lambda + Funda + bunq fan-out
    return HttpResponse.json(MOCK_ONBOARD_RESPONSE);
  }),
];
```

`streamFixture` is a `ReadableStream` that yields fixture lines on a timer — gives you real-feeling token streaming for the demo fallback.

**Five fixtures to write** (each is a `.sse` file, one event per double-blank-line block, exactly the format the backend will emit):

| Fixture | Tests |
|---|---|
| `pure_text.sse` | Deltas → `done: complete`. Baseline streaming. |
| `read_tool_then_text.sse` | Deltas → `tool_call` (read) → `tool_result` → more deltas → `done: complete`. Tests the tool-pill UI. |
| `proposal_flow.sse` | Deltas → `tool_proposal` (move money) → `done: awaiting_approval`. Tests the approval card. |
| `error_midstream.sse` | Deltas → `error` (retryable). Tests reconnection UX. |
| `bootstrap_first_session.sse` | Long agent intro for first session. Tests the populating-dashboard handoff. |

---

## 6. SSE consumer — the only tricky bit on the frontend

`EventSource` is GET-only. We POST. So:

```ts
// src/chat/useChatStream.ts (sketch)
async function streamTurn(sessionId: string, body: TurnRequest, onEvent: (e: SseEvent) => void) {
  const res = await fetch(`/chat/sessions/${sessionId}/turns`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Accept': 'text/event-stream' },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new HttpError(res.status);
  const reader = res.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let idx;
    while ((idx = buffer.indexOf('\n\n')) !== -1) {
      const block = buffer.slice(0, idx); buffer = buffer.slice(idx + 2);
      const ev = parseSseBlock(block); // -> { event, data }
      if (ev) onEvent(ev);
    }
  }
}
```

Edge cases that matter for the demo:

- **Reconnect on transient error**: store last `idempotency_key`, replay POST.
- **401 mid-stream**: refresh Cognito token, replay.
- **Tab visibility**: pause heartbeat-detection while hidden.
- **Stop button**: `AbortController` on the fetch. Server tolerates an abandoned stream — its tool-result is still persisted.

---

## 7. Chat state machine (Zustand)

```ts
type ChatState = {
  sessionId: string;
  messages: Message[];                  // assistant messages may be streaming
  pendingTool: ToolProposal | null;     // presence ⇒ approval card visible
  streamState: 'idle' | 'streaming' | 'awaiting_user' | 'awaiting_approval' | 'error';
  // actions
  sendUserMessage(text: string): Promise<void>;
  approveTool(overrides?: object): Promise<void>;
  denyTool(feedback?: string): Promise<void>;
  resume(): Promise<void>;              // on tab reopen with pendingTool present
};
```

Three rules that make the UI behave:

1. **Composer is always enabled when `streamState !== 'streaming'`**. Even with a `pendingTool`. Per `agent-loop.md §5`, typing during a pending proposal = implicit deny + user message. Send those as two POSTs back-to-back.
2. **`pendingTool` is durable**. On `/chat` mount, fetch session → if backend reports a pending tool, hydrate `pendingTool` and render the card. Tab-close mid-approval is a supported flow.
3. **One in-flight stream at a time per session**. Disable approval buttons while another stream is open.

---

## 8. The approval card (the visible safety rail)

Shadcn `Card` + `Button` + a tiny inline number input for "Edit amount".

```
┌──────────────────────────────────────────────────┐
│ ⚠ Suggested action — needs your approval          │  ← yellow accent border
│                                                  │
│ Move €200 from Buffer → House                     │  ← from `params`, prominent
│                                                  │
│ Why: at current pace this shaves ~3 weeks         │  ← from `rationale`
│ off your timeline.                                │
│                                                  │
│ [ ✓ Approve ]  [ ✎ Edit amount ]  [ Not now ]    │
└──────────────────────────────────────────────────┘
```

Visual rules:

- Yellow/amber border (bunq accent, communicates "action needed").
- Three buttons, `Approve` is primary, others ghost.
- "Edit amount" expands an inline `Input` + confirm — does **not** open a modal.
- "Not now" sends `decision: deny` with empty feedback. If the user types in the composer instead, that's an implicit deny + user message (two POSTs).
- Risk badge in the corner: `risk_level` → low/med/high pill.

---

## 9. Onboarding — the magic moment

Per CLAUDE.md the demo's hero is 0:15–0:45: photo → dashboard populates. This is your most important visual work.

### 9.1 Form flow (full-redirect OAuth)

```
1. /onboard mount
   - if user has no payslip uploaded yet: show step 1
2. Step 1: Payslip
   - drag/drop or file picker → POST /onboard/upload-url → PUT to S3
   - on PUT success: store s3_key in form state
3. Step 2: Funda URL
   - paste, basic regex validation, "manual price?" disclosure
4. Step 3: Connect bunq
   - button → window.location = bunq OAuth URL (full redirect, NOT popup)
   - state token persisted to localStorage so we can resume after redirect
5. Bunq redirects to /auth/callback?bunq_state=...
   - AuthCallbackRoute reads localStorage, restores form, POSTs /onboard
6. POST /onboard returns ProfileSnapshot + session_id
7. Navigate to /chat?bootstrap=session_id
   - ChatRoute detects bootstrap param → opens stream with no inbound user_message
   - PopulatingDashboard animation runs alongside the streaming agent intro
```

**Why localStorage and not sessionStorage:** the bunq redirect lands on a fresh tab context in some browsers. localStorage survives; clear on completion.

### 9.2 The populating animation

This is the demo's win. Not a spinner.

- Skeleton dashboard renders immediately on `/chat?bootstrap=...`.
- As `ProfileSnapshot` arrives, three numbers (gap, months, headroom) count up from 0 with Framer Motion's `useMotionValue` + `animate`. ~800ms.
- Simultaneously, the agent's first SSE stream is rendering token-by-token below.
- Numbers finish before the agent's last sentence. Feels alive.

Keep total animation under 1.5s — judges will be watching the wall clock.

---

## 10. Shell

- **DisclaimerBanner**: thin top strip, dismissible, persists dismissal in localStorage. Copy: *"bunq Nest helps you prepare for homeownership. It is not mortgage advice. When you're ready to apply, bunq connects you with licensed advisors."*
- **HandoffCTA**: bottom-right floating button. Greyed (opacity 0.4, `disabled`) until `profile.projection.months_to_goal <= 6`, then full color. Tooltip on hover explains.
- **Theme**: dark base, bunq teal `#1ec8c8` for primary, bunq yellow `#ffd72e` for accents/approvals. Pin in `tailwind.config.ts`.

---

## 11. 24h timeline (C-only, keyed to CLAUDE.md build order)

| Hours | Task | Verify |
|---|---|---|
| **0–1** | Vite + React + TS scaffold. Tailwind + shadcn init. Routing. Cognito hosted UI redirect (login button → redirect → /auth/callback parses JWT). | Login lands you on `/onboard` with a JWT in memory. |
| **1–2** | MSW setup + 5 fixtures + the `streamTurn` SSE consumer. **Stub `/onboard` endpoints in MSW too.** | A fixture fires `delta` events that render in a bare `<pre>` in `/chat`. |
| **2–4** | `ChatView` + `MessageList` + `AssistantMessage` (streaming) + `Composer`. Zustand store with the state machine. No styling yet. | All 5 fixtures render correctly: text streams, tool pill appears+resolves, approval card shows on proposal, error event surfaces a retry banner. |
| **4–6** | `ApprovalCard` + approve/deny/edit flow. Implicit-deny via composer. Resume-pending-tool on mount. | Approve button POSTs the right shape; refreshing mid-approval still shows the card. |
| **6–9** | `/onboard` form: PayslipUpload (presigned PUT), FundaInput, BunqConnect (full redirect), AuthCallbackRoute, localStorage state preservation. | Full happy path against MSW: upload → funda → bunq mock redirect → /onboard returns snapshot → navigate to /chat. |
| **9–12** | The populating animation. PopulatingDashboard with three counting-up numbers + InsightCard. Visual polish on the chat. Theme tokens, dark mode, bunq accents. | Demo persona (Tim) flow runs end-to-end against MSW in <90s. |
| **12–14** | DisclaimerBanner, HandoffCTA, copy polish, error/empty/loading states. Wire to **real backend** as A & B finish — flip MSW off behind a `?mock=1` query param so the demo fallback survives. | Real first-session flow works against deployed backend. |
| **14–18** | Visual design pass: typography scale, spacing, microcopy, the approval card's yellow accent, the streaming cursor, mobile-ish layout (the demo is desktop but don't break narrow). | Screenshots look like a real product, not a hackathon project. |
| **18–20** | Demo dry-run × 3. Time the flow, fix anything that takes >10s. Pre-cache the demo persona's Funda URL response. Add `?demo=1` mode that uses the curated fixtures end-to-end (offline fallback). | A 90-second demo runs without you touching anything except the form fields. |
| **20–23** | Bug-fix buffer. Submission polish (README screenshots, GitHub cleanup). | All open issues either fixed or explicitly punted. |
| **23–24** | Sleep. Or one more dry run. |

**Slip rules:**
- If hour 6 you're not done with the chat surface → cut "Edit amount" from the approval card. Approve/Deny only.
- If hour 12 onboarding is shaky → use `?demo=1` mode for the video and skip live form completion.
- If hour 16 visual polish is eating time → freeze design, focus on demo dry-runs. A clean v0 beats a half-broken v1.

---

## 12. Demo fallback strategy

**Three fallback layers**, increasingly drastic:

1. **`?mock=1`** — flip MSW on, all backend calls served from fixtures. Only the static dashboard + chat surface render. Use if backend is down.
2. **`?demo=1`** — full curated demo flow with pre-baked timing. Each fixture pre-recorded with realistic delays. Onboarding form auto-fills. Use for the recorded video if live demo gets dicey.
3. **Pre-recorded screen capture** — last resort if everything dies on stage. Per CLAUDE.md the video is recorded ahead anyway.

---

## 13. Open questions to chase down at hour-0 huddle

| # | Who | Question |
|---|---|---|
| 1 | A | Will `tool_proposal.params` include human-readable bucket names, not just IDs? (Otherwise the card needs a fetch to render.) |
| 2 | B | Pin `UploadUrlResponse` and `OnboardRequest`/`OnboardResponse` shapes — write them in `api/types.ts` together. |
| 3 | A | Is the bootstrap session opened by the frontend (`POST /chat/sessions/{id}/turns` with no body?) or does `/onboard` return a session that's already streaming and the frontend just connects? |
| 4 | B | bunq OAuth redirect URL — what's the exact `redirect_uri` we register? Needs to be the deployed Vercel URL plus `localhost:5173` for dev. |
| 5 | A | On approval `overrides`, what fields are editable? Only `amount_eur` for `propose_move_money`? Pin the editable allowlist so the card knows what to show. |
| 6 | A & B | `risk_level` — who decides? Agent at proposal time, or runner deterministically by `amount_eur` thresholds? Doesn't change the UI but affects whether "high" can ever appear. |

Resolve all six in the first 30 minutes. Then nobody talks until lunch.

---

## 14. Things explicitly NOT in scope for C

- Mobile responsive beyond "doesn't look broken at 1280px". Demo is desktop.
- Internationalization. English only.
- Settings / profile edit screens.
- Session list / history browser. Latest session auto-loads. (CLAUDE.md says single session for the demo.)
- Real-time bunq balance ticker. The agent fetches via tools when needed.
- Notifications, weekly check-ins, email — explicitly cut in CLAUDE.md.
- Joint income / partner support — explicitly v2.

If A or B sends you "can we also add…" — the answer per CLAUDE.md is **no**.

---

## 15. Definition of done

C is done when:

- [ ] User signs in via Cognito hosted UI, lands on `/onboard` (first session) or `/chat` (returning).
- [ ] Onboarding form completes end-to-end against real backend with the demo persona's payslip, Funda URL, and bunq sandbox.
- [ ] First chat session opens with the populating animation + streamed agent intro.
- [ ] Subsequent messages stream live, tool pills appear/resolve, approval cards render and round-trip.
- [ ] Disclaimer banner visible. Handoff CTA greyed unless `months_to_goal <= 6`.
- [ ] `?mock=1` and `?demo=1` modes work as offline fallbacks.
- [ ] 90-second happy-path demo runs without intervention.
