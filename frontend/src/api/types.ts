// ─────────────────────────────────────────────────────────────────────────────
// Frontend–backend contracts
// Source of truth: wiki/architecture.md §11
// Mirror this file on the backend. Do NOT diverge.
// ─────────────────────────────────────────────────────────────────────────────

// ---------------------------------------------------------------------------
// §11.1  SSE events — backend → frontend (A owns)
// ---------------------------------------------------------------------------

export type ToolName =
  | 'get_bunq_transactions'
  | 'get_bunq_buckets'
  | 'get_funda_property'
  | 'compute_projection'
  | 'propose_move_money'
  | 'propose_create_bucket'
  | 'propose_handoff_advisor'

export type ProposeMoveMoneyParams = {
  from_bucket_id: string
  from_bucket_name: string   // required — card renders this directly
  to_bucket_id: string
  to_bucket_name: string     // required — card renders this directly
  amount_eur: number
  reason: string
}

export type ProposeCreateBucketParams = {
  name: string
  target_eur?: number
  reason: string
}

export type ToolProposal = {
  tool_use_id: string
  name: 'propose_move_money' | 'propose_create_bucket' | 'propose_handoff_advisor'
  params: ProposeMoveMoneyParams | ProposeCreateBucketParams | Record<string, never>
  summary: string      // one-liner rendered as card headline
  rationale: string    // 1–2 sentences rendered below headline
  risk_level: 'low' | 'medium' | 'high'
}

export type SseEvent =
  | { event: 'delta';         data: { text: string } }
  | { event: 'tool_call';     data: { tool_use_id: string; name: ToolName; params: object; kind: 'read' } }
  | { event: 'tool_result';   data: { tool_use_id: string; ok: boolean; summary?: string; error?: string } }
  | { event: 'tool_proposal'; data: ToolProposal }
  | { event: 'done';          data: { reason: 'complete' | 'awaiting_approval' } }
  | { event: 'error';         data: { message: string; retryable: boolean } }

// ---------------------------------------------------------------------------
// §11.2  Turn request bodies — frontend → backend (A owns)
// ---------------------------------------------------------------------------

export type TurnRequest =
  | {
      type: 'user_message'
      content: string
      idempotency_key: string  // UUIDv4, client-generated; server dedupes for 60s
    }
  | {
      type: 'tool_approval'
      tool_use_id: string
      decision: 'approve' | 'deny'
      overrides?: { amount_eur?: number }  // editable fields only; amount_eur for propose_move_money
      feedback?: string
      idempotency_key: string
    }

// ---------------------------------------------------------------------------
// §11.3  Onboarding endpoints — frontend → backend (B owns)
// Status: proposed by C — needs B sign-off at hour-0 huddle
// ---------------------------------------------------------------------------

// POST /onboard/upload-payslip → PayslipUploadResult
export type PayslipUploadResult = {
  payslip: {
    gross_monthly_eur: number | null
    net_monthly_eur: number | null
    employer_name: string | null
    pay_period: string | null
  }
  confidence: 'high' | 'medium' | 'low'
}

// POST /onboard/parse-funda
export type FundaParseResult = {
  price_eur: number | null
  address: string | null
  size_m2: number | null
  type: string | null
  year_built: number | null
  confidence?: 'high' | 'medium' | 'low'
}

// POST /onboard
export type OnboardRequest = {
  payslip: {
    gross_monthly_eur: number
    net_monthly_eur: number
    employer_name?: string | null
    pay_period?: string | null
    confidence: 'high' | 'medium' | 'low'
  }
  funda_url: string
  funda_price_override_eur?: number  // manual fallback if LLM extraction fails
}
// Note: no bunq_oauth_state — backend uses a static sandbox API key per
// (hard-coded) user_id. See wiki/architecture.md §6.

export type ProfileSnapshot = {
  payslip: {
    gross_monthly_eur: number
    net_monthly_eur: number
    confidence: 'high' | 'medium' | 'low'
  }
  target: {
    price_eur: number
    address: string
  }
  projection: {
    savings_now_eur: number
    deposit_target_eur: number
    gap_eur: number
    monthly_savings_eur: number
    months_to_goal: number
    headroom_range_eur: [number, number]
  }
}

export type OnboardResponse = {
  session_id: string      // first session, ready to stream immediately
  profile: ProfileSnapshot
}

// ---------------------------------------------------------------------------
// Session detail — returned by GET /chat/sessions/{id}
// ---------------------------------------------------------------------------

export type SessionDetail = {
  session_id: string
  profile: ProfileSnapshot
  messages: Message[]          // pre-assembled display history
  pending_tool: ToolProposal | null
}

// ---------------------------------------------------------------------------
// Session / message shapes (internal to frontend)
// ---------------------------------------------------------------------------

export type MessageRole = 'user' | 'assistant'

export type ToolCallRecord = {
  tool_use_id: string
  name: ToolName
  params: object
  result?: { ok: boolean; summary?: string; error?: string }
}

export type Message = {
  id: string
  role: MessageRole
  content: string           // final text; may grow char-by-char while streaming
  streaming?: boolean
  tool_calls?: ToolCallRecord[]
}
