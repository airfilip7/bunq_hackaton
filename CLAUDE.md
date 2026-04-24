# CLAUDE.md

# CLAUDE.md — bunq Nest

Context file for Claude Code and teammates. Read this before writing code.

## One-liner

**bunq Nest** — photograph your payslip, paste a Funda link, see exactly how far you are from the house. Built for bunq Hackathon 7.0 (Multimodal AI, Apr 24–25 2026).

## Product framing (non-negotiable)

This is a **home-buying readiness coach**, not a mortgage advisor. Under Dutch Wft law, recommending specific mortgage products or providers to a specific user is a regulated activity. We stay upstream of that line.

- **We do:** describe the user's position against published norms (Nibud), track savings progress, extract documents into a profile, project timelines, hand off to a licensed advisor when the user is close to their goal.
- **We never do:** recommend products, recommend lenders, recommend term lengths or rate types, tell the user what they "should" do, phrase borrowing capacity as a certainty.

Language discipline — forbidden phrases: "you can afford", "you should", "I recommend", "the best mortgage for you", "you qualify for". Use instead: "per Nibud norms", "typical range", "here's the gap", "when you're ready, connect with a licensed advisor".

A visible disclaimer ships in the UI: *"bunq Nest helps you prepare for homeownership. It is not mortgage advice. When you're ready to apply, bunq connects you with licensed advisors."*

## Hackathon scoring (design against this)

| Criterion | Weight | Our angle |
|---|---|---|
| Impact & Usefulness | 30% | Dutch first-time buyers are paralyzed — this makes the path concrete in 10 seconds |
| Innovation & Creativity | 25% | Document vision + agentic projection over live bunq data is a novel combination |
| Technical Execution | 20% | Clean VLM/LLM split, structured outputs, real multimodal (not bolted on) |
| bunq Integration | 15% | Uses bunq transaction data + buckets + ends with bunq's real advisor handoff |
| Presentation & Pitch | 10% | One protagonist, one moment of magic, one crisp handoff line |

The largest bucket is Impact. The most important question is "would people actually use this?" — keep it as the north star.

## The only user flow that matters

The product has two surfaces: a one-time onboarding form, and the chat that lives after it.

**First session (onboarding, once per user):**

1. Sign in via Cognito (email + password).
2. App detects `onboarded == false` → routes to the onboarding form.
3. User photographs latest Dutch payslip (loonstrook), pastes a Funda URL, completes bunq OAuth.
4. Form submits → backend uploads payslip to S3, triggers the Lambda extractor (Bedrock vision), parses the Funda URL, pulls a bunq snapshot, persists the profile to DynamoDB.
5. Backend bootstraps Session #1: synthetic context turn → opens an SSE stream → chat agent's first message streams in with three numbers (gap to deposit, months to goal, mortgage headroom range) and one insight sentence.

**Every session after that:**

6. Sign in → app routes straight to `/chat`. Profile + most-recent session + a fresh bunq snapshot are loaded server-side. Agent opens with a "welcome back" turn that streams in.
7. User chats. Agent can re-run read tools (transactions, buckets, projection, Funda) silently and continue. Whenever the agent wants to *do* something — move money, create a bucket — it emits a `propose_*` tool call and the chat shows an inline approval card. Nothing changes in bunq without explicit user approval.
8. Greyed-out advisor-handoff CTA stays visible. Lights up when the user is within ~6 months of goal.

End-to-end first-session demo in ~90 seconds. Repeat-session demo in <10s to a populated chat.

## Architecture

> Full system design lives in `wiki/architecture.md`, `wiki/agent-loop.md`, and `wiki/data-model.md`. The summary below is what every contributor needs in their head.

```
                ┌──────────────┐
                │ React + Vite │
                └──────┬───────┘
                       │ HTTPS (REST + SSE)
                       ▼
              ┌────────────────────┐
              │ FastAPI (App Runner│         ┌─────────────────┐
              │ or ECS Fargate)    │ ──────▶ │  Bedrock        │
              │ - /onboard         │         │  - Claude vision│
              │ - /chat (SSE)      │         │  - Sonnet 4.6   │
              │ - /bunq oauth      │         └─────────────────┘
              └────┬──────┬────────┘
                   │      │
        S3 PUT     │      │ DynamoDB single table
        ┌──────────▼─┐    │ (Users, Sessions, Turns,
        │ payslip-   │    │  ToolRuns, BunqTokens,
        │ imgs/...   │    │  PendingTool)
        └─────┬──────┘    │
              │ ObjectCreated / sync invoke
              ▼
        ┌─────────────┐
        │ Lambda:     │ ──▶ Bedrock vision ──▶ extracted JSON ──▶ DynamoDB
        │ payslip-    │
        │ extract     │
        └─────────────┘
                                                ┌─────────────────┐
                                                │ bunq Public API │
                                                │ (OAuth-scoped)  │
                                                └─────────────────┘
```

**The two AI invocations:**

- **Vision (Anthropic on Bedrock):** payslip extraction. Runs in a Lambda triggered from `/onboard`. Returns `{gross_monthly_eur, net_monthly_eur, employer_name, pay_period, confidence}`. Image lives in S3 (KMS-encrypted, 30d TTL).
- **Chat agent (Sonnet 4.6 on Bedrock):** the ongoing surface. Tool-using agent loop. Read-only tools (`get_bunq_transactions`, `get_bunq_buckets`, `get_funda_property`, `compute_projection`) auto-execute inside one SSE stream. Write tools (`propose_move_money`, `propose_create_bucket`) emit a structured proposal, end the stream, and wait for user approval. Funda parsing happens via a `get_funda_property` tool the agent can call on demand.

**Two safety rails the runner enforces, not the model:**

1. The Wft-safe coaching system prompt (canonical in `## Prompts`, imported from `backend/prompts.py`). Same prompt as before — unchanged by the AWS move.
2. The read-vs-write tool split. Any tool whose name does not start with `propose_` is allowed to auto-execute. Any `propose_*` tool *must* go through the approval lane before its side effect runs. Hard-coded check in the agent runner — not a property of the model.

**Streaming choice (and why):** SSE, not WebSockets. The agent-to-user dataflow is one-way streaming text. SSE is one HTTP response, sails through ALB and CloudFront without sticky-session config, and is dead-simple to debug in a browser. User input is plain `POST`. WebSockets buy nothing here. See `wiki/agent-loop.md` for the full event schema.

**Session-state choice (and why):** DynamoDB single-table. AWS-native, no connection pool from Lambda or App Runner, scales to zero, indexes well by `user_id` and `session_id`. Pending approvals are durable rows — closing the tab mid-action keeps the proposal waiting for next session. See `wiki/data-model.md`.

## Stack

- **Frontend:** React + Vite. Two routes: `/onboard` (one-time form) and `/chat` (the rest of the product). Dark theme, bunq teal/yellow accents.
- **Backend:** Python FastAPI on AWS App Runner (ECS Fargate is the fallback). Endpoints:
  - `POST /onboard/upload-url` — returns a presigned S3 PUT URL.
  - `POST /onboard` — `{s3_key, funda_url, bunq_oauth_code}` → triggers payslip Lambda, parses Funda, completes bunq OAuth, writes profile, bootstraps Session #1.
  - `POST /chat/sessions/{id}/turns` — SSE-streamed turn endpoint. Accepts `user_message`, `tool_approval`. See `wiki/agent-loop.md`.
  - `GET /chat/sessions` and `GET /chat/sessions/{id}` — list / load session metadata + history.
  - `GET /bunq/oauth/callback` — completes the OAuth code-for-token exchange.
- **Auth:** Amazon Cognito user pool (hosted UI). JWT verified on every request.
- **Inference:** Amazon Bedrock, region `eu-central-1`. Anthropic Claude vision for payslip; Claude Sonnet 4.6 for the chat agent. Pin model ids in `backend/anthropic_client.py` (confirm exact Bedrock model ids at build time — Sonnet 4.6 availability on Bedrock may lag the direct API; if so, fall back to current Sonnet vision).
- **Storage:** DynamoDB on-demand single table `bunq-nest-main`. S3 bucket `bunq-nest-uploads-eu-central-1` for payslip images (KMS-encrypted, 30d lifecycle on originals). bunq tokens encrypted with KMS key `alias/bunq-tokens` before being stored.
- **bunq data:** real bunq Public API via OAuth from the start. Token handling in `backend/bunq_client.py`. **[risk]** OAuth in 24h is non-trivial — if we're behind at the 12h checkpoint, fall back to a `BunqClient` stub that reads fixture JSON. The agent loop and data model don't change.
- **Deployment:** Vercel for frontend, App Runner for backend, Lambda for image extraction. All AWS resources in `eu-central-1`. Demo runs off deployed URLs; keep a local FastAPI + fixture-mode bunq fallback ready.

Call out Claude + AWS in the pitch — both are sponsors.

## Demo persona

Tim, 31, data engineer in Utrecht. €62k gross. Renting with Eva for 4 years. €34k combined savings. Target: €55k deposit on a ~€425k apartment. 6 months of realistic bunq transactions seeded in mock data (salary in, rent out, groceries, leisure, ending at €34k in a savings bucket).

UI language: English. VLM prompt handles Dutch payslip content but surfaces English labels.

Single-user MVP (no joint income math). Partner/joint support is v2.

## Prompts (canonical)

### VLM — payslip extraction

```
You are extracting data from a Dutch payslip (loonstrook). Return ONLY valid JSON
matching this schema:
{
  "gross_monthly_eur": number | null,
  "net_monthly_eur": number | null,
  "employer_name": string | null,
  "pay_period": string | null,
  "confidence": "high" | "medium" | "low"
}
If any field is unreadable, set it to null. Do not infer missing values.
Do not include any text outside the JSON.
```

### LLM — Funda extraction

Feed the fetched HTML (truncated to ~8k tokens). Ask for the same JSON shape as
`/parse-funda` output. Regex fallback for price in case the LLM call fails.

### LLM — coaching agent (system prompt)

```
You are a goal-tracking assistant for home-buying preparation. You describe
the user's financial position relative to Nibud's published norms and their
stated goal.

You NEVER recommend specific mortgage products, lenders, term lengths, or
rate types. You NEVER tell the user what they "should" do. You describe
gaps, ranges, and trajectories.

All figures for borrowing capacity are presented as ranges with the phrase
"per Nibud norms" attached.

If the user asks for a recommendation, respond: "That's a question for a
licensed advisor. I can help you prepare to ask them the right questions."

Output strictly the JSON schema provided. No prose outside JSON.
```

Include this system prompt verbatim in the README and mention it in the demo — the bunq judges will notice.

## Features IN the MVP

- Payslip photo upload + VLM extraction (single document type).
- Funda URL paste + LLM extraction (manual price fallback).
- Savings projection over mock bunq transactions.
- Mortgage headroom as a **range** with Nibud disclaimer.
- One dashboard screen with three numbers + one insight card.
- Greyed handoff CTA with disclaimer.

## Features explicitly CUT

- Voice interface (user testing said no).
- Auto-sweep from buckets to House bucket.
- BKR / jaaropgaaf / rental contract scanning.
- Funda screenshot as second VLM flow.
- Scenario sliders ("what if I skip a holiday").
- Education / "what is NHG" explainers.
- Partner / joint income.
- Weekly check-ins / notifications.
- Real advisor handoff logic beyond a greyed-out button.

If mid-build someone says "can we also add…" — the answer is **no**.

## Build order (24 hours)

- **0–2h:** Repo, Vercel, FastAPI skeleton, Anthropic API key. UI skeleton started. Mock data drafted. Funda scraper spike.
- **2–8h:** Payslip extraction end-to-end (image in → JSON out → rendered). **Riskiest path — do this first.**
- **8–12h:** Funda URL parsing + projection math + populated dashboard.
- **12–16h:** Polish. "Populating" animation (the demo's magic moment). Copy. Disclaimer. Greyed handoff.
- **16–20h:** Record demo video. Rehearse pitch 5× before recording.
- **20–23h:** Devpost submission, README, GitHub cleanup.
- **23–24h:** Sleep or final dry run.

## Demo prep

- **One real payslip image**, tested against the VLM ≥20 times before demo day. If it fails 1/20, it'll fail on stage — iterate the prompt until it's bulletproof.
- **Three pre-tested Funda URLs** in different price bands (€325k, €450k, €600k) in case Q&A probes.
- **Mock transactions** realistic enough that the projection numbers look believable.
- Local fallback ready in case the deployed version flakes.

## Demo video beats (target 2:30)

1. **0:00–0:15** — "Meet Tim. 31, Utrecht, been saying 'we're buying a house soon' for four years."
2. **0:15–0:45** — App open → tap "Add my income" → photograph payslip on kitchen table → dashboard populates. **Hold on this moment.**
3. **0:45–1:15** — Paste Funda URL → gap / months / headroom appear. VO: "In 30 seconds, Tim knows more about his home-buying position than he did after a year of spreadsheets."
4. **1:15–1:50** — Zoom into the insight card. Narrate the savings-rate projection.
5. **1:50–2:10** — Point at the greyed handoff. "bunq Nest doesn't give advice. When Tim's ready, bunq connects him to a licensed advisor. Not a day sooner."
6. **2:10–2:30** — Close. Product name + tagline + sponsor callouts ("Built with Claude vision on AWS") + one Impact number.

## Pitch opener

> "82% of Dutch first-time buyers under 35 don't know how close they actually are. We fixed that in one photo."

Find a real CBS/DNB stat if possible; a real number in the first 10 seconds locks in Impact.

## The regulatory objection (rehearsed answer)

A judge will ask: "isn't this mortgage advice?" Answer in one breath:

> "No. We help people save toward a goal they've already chosen, extract their own documents into their own profile, and compare that profile to publicly published norms. We don't recommend products, don't compare lenders, and don't tell users what to do. When they're ready to decide, we hand them to a licensed advisor — that's a feature, not a disclaimer."

## Competitive positioning (what we beat)

Nothing existing combines real bank data + document intelligence + goal projection in one place:

- **Nibud calculator:** doesn't know bank balance.
- **bunq:** doesn't read jaaropgaafs or payslips.
- **Funda:** doesn't know the user's finances.
- **Hypotheker / Independer:** forget the user on tab close.
- **Viisi:** great advisors, but premature until user is close.
- **User's own spreadsheet:** knows only what they type.

bunq Nest lives inside the bank, ingests documents in 30 seconds, uses real transaction data, and nudges when something actually changes.

## Repo layout (suggested)

```
bunq-nest/
├── CLAUDE.md              # this file
├── README.md              # setup + demo instructions
├── frontend/              # React + Vite
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/    # Dashboard, PayslipUpload, FundaInput, InsightCard
│   │   └── api/           # thin client for FastAPI endpoints
│   └── package.json
├── backend/               # FastAPI
│   ├── main.py            # three endpoints
│   ├── prompts.py         # VLM + LLM prompts (canonical, imported elsewhere)
│   ├── anthropic_client.py
│   ├── funda.py           # HTML fetch + parse
│   ├── projection.py      # Nibud math + agent call
│   └── mocks/
│       └── transactions.json
└── demo/
    ├── payslip_tim.jpg    # test image
    └── funda_urls.txt     # pre-tested URLs
```

## Open questions / assumptions to verify

- Confirm exact Claude model string for vision + text at build time (docs: https://docs.claude.com).
- Nibud's published multiplier for 2026 — look up at start of build; don't hardcode from memory.
- Funda's HTML structure may have bot protection; have a fallback plan (manual price entry is already in scope, so not a blocker).
- Confirm the demo venue has reliable wifi; if not, pre-cache responses for demo persona and add a "demo mode" toggle.


# Guidelines 
## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

