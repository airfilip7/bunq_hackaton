import { http, HttpResponse } from "msw";
import type { OnboardResponse } from "@/api/types";

// ---------------------------------------------------------------------------
// Fixture loader — streams an .sse file line-by-line with a delay.
// ---------------------------------------------------------------------------

async function* sseLines(text: string, delayMs = 40) {
  const blocks = text.trim().split("\n\n");
  for (const block of blocks) {
    await new Promise((r) => setTimeout(r, delayMs));
    yield new TextEncoder().encode(block + "\n\n");
  }
}

function streamFixture(text: string, delayMs = 40): ReadableStream<Uint8Array> {
  const gen = sseLines(text, delayMs);
  return new ReadableStream({
    async pull(ctrl) {
      const { value, done } = await gen.next();
      if (done) ctrl.close();
      else ctrl.enqueue(value);
    },
  });
}

// ---------------------------------------------------------------------------
// Fixture files (imported as raw strings via ?raw)
// ---------------------------------------------------------------------------

import pureText from "./fixtures/pure_text.sse?raw";
import readTool from "./fixtures/read_tool_then_text.sse?raw";
import proposalFlow from "./fixtures/proposal_flow.sse?raw";
import bootstrapSession from "./fixtures/bootstrap_first_session.sse?raw";

// Pick a fixture based on the request body.
function pickFixture(body: { type: string; content?: string }): string {
  if (body.content === "__bootstrap__") return bootstrapSession;
  if (body.type === "tool_approval") return pureText; // approval confirmation
  // Cycle through scenarios for regular messages (useful for demos).
  const scenarios = [pureText, readTool, proposalFlow];
  const idx = Math.floor(Math.random() * scenarios.length);
  return scenarios[idx];
}

// ---------------------------------------------------------------------------
// Mock onboard response — Tim's demo persona (matches CLAUDE.md)
// ---------------------------------------------------------------------------

const MOCK_ONBOARD: OnboardResponse = {
  session_id: "mock-session-001",
  profile: {
    payslip: {
      gross_monthly_eur: 5167,
      net_monthly_eur: 3520,
      confidence: "high",
    },
    target: { price_eur: 425000, address: "Utrecht, NL" },
    projection: {
      savings_now_eur: 34000,
      deposit_target_eur: 55000,
      gap_eur: 21000,
      monthly_savings_eur: 1450,
      months_to_goal: 14,
      headroom_range_eur: [285000, 320000],
    },
  },
};

// ---------------------------------------------------------------------------
// Handlers
// ---------------------------------------------------------------------------

export const handlers = [
  // Chat turn — SSE stream
  http.post("/chat/sessions/:id/turns", async ({ request }) => {
    const body = (await request.json()) as { type: string; content?: string };
    const fixture = pickFixture(body);
    return new HttpResponse(streamFixture(fixture, 35), {
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-store",
        "X-Accel-Buffering": "no",
      },
    });
  }),

  // Presigned upload URL
  http.post("/onboard/upload-url", () =>
    HttpResponse.json({
      upload_url: "http://localhost:5173/__mock_s3_put",
      s3_key: `mock-payslip-${Date.now()}.jpg`,
      expires_at: Date.now() + 300_000,
      required_headers: { "Content-Type": "image/jpeg" },
    }),
  ),

  // S3 PUT (mock bucket)
  http.put(
    "http://localhost:5173/__mock_s3_put",
    () => new HttpResponse(null, { status: 200 }),
  ),

  // Funda parse — simulates backend fetching + LLM extraction
  http.post("/onboard/parse-funda", async ({ request }) => {
    const { url } = (await request.json()) as { url: string };
    await new Promise((r) => setTimeout(r, 900)); // simulate fetch + LLM
    // Extract a slug from the URL to make the mock feel realistic
    const slug = url.split("/").filter(Boolean).pop() ?? "listing";
    const address = slug
      .replace(/^(huis|appartement|woning)-\d+-/, "")
      .replace(/-/g, " ")
      .replace(/\/$/, "")
      .replace(/\b\w/g, (c) => c.toUpperCase());
    return HttpResponse.json({
      price_eur: 425000,
      address: address || "Listing",
      size_m2: 78,
      property_type: "huis",
      confidence: "high",
    });
  }),

  // Onboard submit — simulates Lambda + Funda + bunq fan-out delay
  http.post("/onboard", async () => {
    await new Promise((r) => setTimeout(r, 2500));
    return HttpResponse.json(MOCK_ONBOARD);
  }),

  // Session list
  http.get("/chat/sessions", () =>
    HttpResponse.json([
      { session_id: "mock-session-001", started_at: Date.now() },
    ]),
  ),

  // Session detail — returns history + profile for session resume
  http.get("/chat/sessions/:id", ({ params }) =>
    HttpResponse.json({
      session_id: params.id,
      profile: MOCK_ONBOARD.profile,
      messages: [
        {
          id: "resume-msg-1",
          role: "assistant",
          content:
            "Welcome back, Tim! Your savings are still at €34,000 — you're 14 months from your deposit target. " +
            "What would you like to focus on today?",
          streaming: false,
          tool_calls: [],
        },
      ],
      pending_tool: null,
    }),
  ),
];
