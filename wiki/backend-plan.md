# Backend implementation plan

Phased build order for the bunq Nest backend. Each phase is independently deployable and testable. Read alongside `architecture.md`, `data-model.md`, and `agent-loop.md`.

---

## Phase 0 — Infrastructure bootstrap

**Goal:** FastAPI skeleton running locally + AWS resources provisioned. No AI calls yet.

- `backend/` project scaffold with `requirements.txt`, `config.py`, `main.py`
- `config.py` — pydantic-settings, reads from env vars; all table/bucket/model ids in one place
- `main.py` — FastAPI app, CORS, `GET /health` → `{status: ok}`
- `backend/dynamo.py` — boto3 DynamoDB client + typed helpers for every access pattern in `data-model.md`
- `backend/s3.py` — boto3 S3 client + presigned PUT URL generation
- `backend/prompts.py` — canonical VLM + coaching prompts (no model calls, just strings)
- `backend/mocks/transactions.json` — Tim's realistic 6-month transaction fixture
- AWS: DynamoDB table `bunq-nest-main` (PK/SK + GSI1) provisioned in `us-east-1`
- AWS: S3 bucket `bunq-nest-uploads-us-east-1` (SSE-S3, block public access, 30d lifecycle on originals)

**Done when:** `uvicorn backend.main:app` runs, `/health` returns 200, `aws dynamodb describe-table` and `aws s3 ls` confirm resources exist.

---

## Phase 1 — Payslip extraction

**Goal:** Upload a payslip image, get structured JSON back via Bedrock vision.

- `POST /onboard/upload-url` — returns presigned S3 PUT URL
- `backend/payslip.py` — invoke Bedrock vision (Claude 3.5 Sonnet), parse response into `PayslipExtract` schema
- Write extracted JSON to `Users#{user_id}` profile item in DynamoDB
- Error path: `confidence: "low"` returned as-is to the caller; frontend will prompt manual entry

**Done when:** curl with a real payslip JPEG → JSON with gross/net/employer.

---

## Phase 2 — Funda parsing + projection

**Goal:** Paste a Funda URL, compute the three dashboard numbers.

- `backend/funda.py` — `httpx` fetch + Claude Sonnet text extraction + regex fallback for price
- `backend/projection.py` — deterministic Nibud math: deposit target, gap, months to goal, headroom range
- `POST /onboard` — orchestrates Phase 1 + Phase 2, writes full profile, creates Session #1
- `GET /chat/sessions` and `GET /chat/sessions/{id}` — list/load sessions from DynamoDB

**Done when:** POST /onboard with s3_key + funda_url returns a populated profile + session.

---

## Phase 3 — Chat agent (SSE streaming)

**Goal:** Working agent loop, read tools auto-execute, write tools pause for approval.

- `POST /chat/sessions/{session_id}/turns` — SSE endpoint, accepts `user_message` or `tool_approval`
- `backend/agent.py` — Bedrock streaming loop per `agent-loop.md` pseudocode
- Read tools implemented: `get_bunq_transactions`, `get_bunq_buckets`, `get_funda_property`, `compute_projection`
- Write tools stubbed: `propose_move_money`, `propose_create_bucket` — emit proposal, pause stream
- All tool calls persisted to DynamoDB (Turns + ToolRuns + PendingTool)
- Cognito JWT middleware verifying every request

**Done when:** full SSE turn cycle works end-to-end with mock bunq data.

---

## Phase 4 — bunq OAuth + real data

**Goal:** Real bunq transaction + bucket data flowing through the agent.

- `GET /bunq/oauth/callback` — code exchange, KMS-encrypt tokens, store in DynamoDB
- `backend/bunq_client.py` — BunqClient with real API calls; stubbed fallback reads fixture JSON
- Write tool execution: `propose_move_money` and `propose_create_bucket` call real bunq API after approval
- Token refresh on 401, re-auth prompt surfaced in chat on failure

**[risk]** If behind at 12h checkpoint, ship stub BunqClient reading `mocks/transactions.json` — architecture is unchanged.

**Done when:** live bunq account shows up in the agent's projection, or fixture mode confirmed working for demo.

---

## Phase 5 — Polish + deployment

**Goal:** Demo-ready, deployed, rehearsed.

- Vercel deploy for frontend (separate repo/folder)
- App Runner or ECS Fargate deploy for backend (Dockerfile)
- CloudWatch Logs wired, one simple dashboard
- Demo mode toggle (pre-caches Tim's responses, survives wifi loss)
- README with setup instructions + demo script
- Three pre-tested Funda URLs in `demo/funda_urls.txt`
- Final dry-run: payslip upload → dashboard → Funda → chat → proposal card

---

## Region note

Architecture docs say `eu-central-1`. Hackathon credentials are scoped to `us-east-1`. All AWS resources provisioned in `us-east-1` for the hackathon build. Update `config.py` `AWS_REGION` if credentials change.
