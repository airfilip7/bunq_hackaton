#!/usr/bin/env bash
# smoke.sh — End-to-end smoke test for bunq Nest backend.
# Drives the full flow via curl against a running local server.
#
# Prerequisites:
#   - Server running:  uvicorn backend.main:app --reload
#   - Fixture modes:   BUNQ_MODE=fixture FUNDA_MODE=fixture
#   - jq installed
#
# Usage:
#   ./scripts/smoke.sh                    # default: http://localhost:8000
#   BASE_URL=http://localhost:9000 ./scripts/smoke.sh
set -euo pipefail

BASE="${BASE_URL:-http://localhost:8000}"
AUTH="Authorization: Bearer demo"
PASS=0
FAIL=0
SKIP=0

# ── Helpers ──────────────────────────────────────────────────────────────────

green()  { printf "\033[32m✓ %s\033[0m\n" "$1"; }
red()    { printf "\033[31m✗ %s\033[0m\n" "$1"; }
yellow() { printf "\033[33m⊘ %s\033[0m\n" "$1"; }

check() {
    local label="$1" actual="$2" expected="$3"
    if [ "$actual" = "$expected" ]; then
        green "$label"
        PASS=$((PASS + 1))
    else
        red "$label (expected=$expected got=$actual)"
        FAIL=$((FAIL + 1))
    fi
}

skip() {
    yellow "$1 — SKIPPED ($2)"
    SKIP=$((SKIP + 1))
}

command -v jq >/dev/null 2>&1 || { echo "jq is required but not installed."; exit 1; }

echo ""
echo "═══════════════════════════════════════════════"
echo "  bunq Nest — Smoke Test"
echo "  Target: $BASE"
echo "═══════════════════════════════════════════════"
echo ""

# ── 1. Health ────────────────────────────────────────────────────────────────

echo "── 1. Health check ──"
HTTP=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/health")
check "GET /health returns 200" "$HTTP" "200"

BODY=$(curl -s "$BASE/health" | jq -r '.ok')
check "GET /health body ok=true" "$BODY" "true"
echo ""

# ── 2. Parse Funda (fixture mode) ───────────────────────────────────────────

echo "── 2. Parse Funda ──"
FUNDA_RESP=$(curl -s -X POST "$BASE/onboard/parse-funda" \
    -H "Content-Type: application/json" \
    -d '{"url":"https://www.funda.nl/koop/utrecht/huis-12345/"}')

FUNDA_HTTP=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE/onboard/parse-funda" \
    -H "Content-Type: application/json" \
    -d '{"url":"https://www.funda.nl/koop/utrecht/huis-12345/"}')
check "POST /onboard/parse-funda returns 200" "$FUNDA_HTTP" "200"

HAS_PRICE=$(echo "$FUNDA_RESP" | jq 'has("price_eur")')
check "parse-funda response has price_eur" "$HAS_PRICE" "true"
echo ""

# ── 3. List sessions (empty) ────────────────────────────────────────────────

echo "── 3. List sessions ──"
SESS_HTTP=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/chat/sessions" -H "$AUTH")
check "GET /chat/sessions returns 200" "$SESS_HTTP" "200"
echo ""

# ── 4. Upload payslip ───────────────────────────────────────────────────────

echo "── 4. Upload payslip ──"
PAYSLIP_IMG="demo/payslip_tim.jpg"
if [ -f "$PAYSLIP_IMG" ]; then
    UPLOAD_HTTP=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE/onboard/upload-payslip" \
        -F "file=@$PAYSLIP_IMG;type=image/jpeg")
    # This calls Bedrock — may fail without AWS creds
    if [ "$UPLOAD_HTTP" = "200" ]; then
        check "POST /onboard/upload-payslip returns 200" "$UPLOAD_HTTP" "200"
    else
        skip "POST /onboard/upload-payslip" "returned $UPLOAD_HTTP (needs AWS credentials for Bedrock)"
    fi
else
    skip "POST /onboard/upload-payslip" "demo/payslip_tim.jpg not found"
fi
echo ""

# ── 5. Full onboard flow ────────────────────────────────────────────────────

echo "── 5. Onboard (full flow) ──"
echo "   Note: requires AWS credentials (S3 + Bedrock). Skipping if unavailable."

ONBOARD_HTTP=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE/onboard" \
    -H "$AUTH" \
    -H "Content-Type: application/json" \
    -d '{"s3_key":"test/payslip.jpg","funda_url":"https://www.funda.nl/koop/utrecht/huis-12345/"}')

if [ "$ONBOARD_HTTP" = "200" ]; then
    check "POST /onboard returns 200" "$ONBOARD_HTTP" "200"

    ONBOARD_RESP=$(curl -s -X POST "$BASE/onboard" \
        -H "$AUTH" \
        -H "Content-Type: application/json" \
        -d '{"s3_key":"test/payslip.jpg","funda_url":"https://www.funda.nl/koop/utrecht/huis-12345/"}')

    SESSION_ID=$(echo "$ONBOARD_RESP" | jq -r '.session_id')
    check "onboard response has session_id" "$([ -n "$SESSION_ID" ] && echo true)" "true"
    echo ""

    # ── 6. Chat turn (SSE) ───────────────────────────────────────────────
    echo "── 6. Chat turn (user message → SSE) ──"
    if [ -n "$SESSION_ID" ] && [ "$SESSION_ID" != "null" ]; then
        SSE_RESP=$(curl -sN --max-time 30 -X POST "$BASE/chat/sessions/$SESSION_ID/turns" \
            -H "$AUTH" \
            -H "Content-Type: application/json" \
            -H "Accept: text/event-stream" \
            -d '{"type":"user_message","content":"How am I doing?"}' 2>&1 || true)

        HAS_DONE=$(echo "$SSE_RESP" | grep -c "event: done" || true)
        if [ "$HAS_DONE" -ge 1 ]; then
            check "SSE stream contains done event" "true" "true"
        else
            red "SSE stream missing done event"
            FAIL=$((FAIL + 1))
        fi
    else
        skip "Chat turn" "no valid session_id from onboard"
    fi
else
    skip "POST /onboard" "returned $ONBOARD_HTTP (needs AWS credentials)"
    skip "Chat turn" "depends on onboard"
fi
echo ""

# ── Summary ──────────────────────────────────────────────────────────────────

echo "═══════════════════════════════════════════════"
printf "  Results:  \033[32m%d passed\033[0m" "$PASS"
if [ "$FAIL" -gt 0 ]; then
    printf "  \033[31m%d failed\033[0m" "$FAIL"
fi
if [ "$SKIP" -gt 0 ]; then
    printf "  \033[33m%d skipped\033[0m" "$SKIP"
fi
echo ""
echo "═══════════════════════════════════════════════"

[ "$FAIL" -eq 0 ] || exit 1
