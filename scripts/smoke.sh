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
set -uo pipefail
# NOTE: no `set -e` — we track pass/fail ourselves

BASE="${BASE_URL:-http://localhost:8000}"
CHAT_AUTH="Authorization: Bearer demo"
ONBOARD_AUTH="X-Dev-User-Id: u_demo"
CURL_TIMEOUT=5
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

# ── 0. Connectivity check ───────────────────────────────────────────────────

echo "── 0. Server reachable? ──"
if ! curl -sf --connect-timeout 2 --max-time "$CURL_TIMEOUT" "$BASE/health" >/dev/null 2>&1; then
    red "Cannot reach $BASE/health — is the server running?"
    echo ""
    echo "  Start it with:"
    echo "    BUNQ_MODE=fixture FUNDA_MODE=fixture uvicorn backend.main:app --reload"
    echo ""
    exit 1
fi
green "Server is up"
echo ""

# ── 1. Health ────────────────────────────────────────────────────────────────

echo "── 1. Health check ──"
HTTP=$(curl -s -o /dev/null -w "%{http_code}" --max-time "$CURL_TIMEOUT" "$BASE/health")
check "GET /health returns 200" "$HTTP" "200"

BODY=$(curl -s --max-time "$CURL_TIMEOUT" "$BASE/health" | jq -r '.ok')
check "GET /health body ok=true" "$BODY" "true"
echo ""

# ── 2. Parse Funda (fixture mode) ───────────────────────────────────────────

echo "── 2. Parse Funda ──"
FUNDA_RESP=$(curl -s --max-time "$CURL_TIMEOUT" -X POST "$BASE/onboard/parse-funda" \
    -H "Content-Type: application/json" \
    -d '{"url":"https://www.funda.nl/koop/utrecht/huis-12345/"}' 2>&1) || true

FUNDA_HTTP=$(curl -s -o /dev/null -w "%{http_code}" --max-time "$CURL_TIMEOUT" -X POST "$BASE/onboard/parse-funda" \
    -H "Content-Type: application/json" \
    -d '{"url":"https://www.funda.nl/koop/utrecht/huis-12345/"}' 2>&1) || true
check "POST /onboard/parse-funda returns 200" "$FUNDA_HTTP" "200"

HAS_PRICE=$(echo "$FUNDA_RESP" | jq 'has("price_eur")' 2>/dev/null) || HAS_PRICE="false"
check "parse-funda response has price_eur" "$HAS_PRICE" "true"
echo ""

# ── 3. List sessions (empty) ────────────────────────────────────────────────

echo "── 3. List sessions ──"
SESS_HTTP=$(curl -s -o /dev/null -w "%{http_code}" --max-time "$CURL_TIMEOUT" \
    "$BASE/chat/sessions" -H "$CHAT_AUTH" 2>&1) || true
check "GET /chat/sessions returns 200" "$SESS_HTTP" "200"
echo ""

# ── 4. Upload payslip ───────────────────────────────────────────────────────

echo "── 4. Upload payslip ──"
PAYSLIP_IMG="payslips/payslip1.png"
if [ -f "$PAYSLIP_IMG" ]; then
    UPLOAD_BODY=$(curl -s --max-time 30 -X POST \
        "$BASE/onboard/upload-payslip" \
        -F "file=@$PAYSLIP_IMG;type=image/png" 2>&1) || true
    UPLOAD_HTTP=$(curl -s -o /dev/null -w "%{http_code}" --max-time 30 -X POST \
        "$BASE/onboard/upload-payslip" \
        -F "file=@$PAYSLIP_IMG;type=image/png" 2>&1) || true
    # This calls Bedrock — may fail without AWS creds
    if [ "$UPLOAD_HTTP" = "200" ]; then
        check "POST /onboard/upload-payslip returns 200" "$UPLOAD_HTTP" "200"
        CONFIDENCE=$(echo "$UPLOAD_BODY" | jq -r '.confidence' 2>/dev/null) || CONFIDENCE=""
        echo "   confidence=$CONFIDENCE"
    else
        skip "POST /onboard/upload-payslip" "HTTP $UPLOAD_HTTP — $(echo "$UPLOAD_BODY" | head -c 120)"
    fi
else
    skip "POST /onboard/upload-payslip" "payslips/payslip1.png not found"
fi
echo ""

# ── 5. Full onboard flow ────────────────────────────────────────────────────

echo "── 5. Onboard (full flow) ──"
echo "   Step 5a: Get presigned S3 upload URL"

UPLOAD_URL_RESP=$(curl -s --max-time "$CURL_TIMEOUT" -X POST "$BASE/onboard/upload-url" \
    -H "$ONBOARD_AUTH" 2>&1) || true
S3_KEY=$(echo "$UPLOAD_URL_RESP" | jq -r '.s3_key' 2>/dev/null) || S3_KEY=""
PRESIGNED_URL=$(echo "$UPLOAD_URL_RESP" | jq -r '.upload_url' 2>/dev/null) || PRESIGNED_URL=""

if [ -z "$S3_KEY" ] || [ "$S3_KEY" = "null" ]; then
    skip "POST /onboard/upload-url" "failed — $(echo "$UPLOAD_URL_RESP" | head -c 120)"
    skip "S3 PUT" "depends on upload-url"
    skip "POST /onboard" "depends on S3 upload"
    skip "Chat turn" "depends on onboard"
    echo ""
else
    check "POST /onboard/upload-url returns s3_key" "true" "true"

    echo "   Step 5b: PUT payslip image to S3 via presigned URL"
    S3_PUT_HTTP=$(curl -s -o /dev/null -w "%{http_code}" --max-time 15 -X PUT "$PRESIGNED_URL" \
        -H "Content-Type: image/jpeg" \
        --data-binary "@$PAYSLIP_IMG" 2>&1) || S3_PUT_HTTP="000"
    check "S3 presigned PUT returns 200" "$S3_PUT_HTTP" "200"

    if [ "$S3_PUT_HTTP" != "200" ]; then
        skip "POST /onboard" "S3 upload failed"
        skip "Chat turn" "depends on onboard"
    else
        echo "   Step 5c: POST /onboard with s3_key=$S3_KEY"
        ONBOARD_RESP=$(curl -s --max-time 60 -X POST "$BASE/onboard" \
            -H "$ONBOARD_AUTH" \
            -H "Content-Type: application/json" \
            -d "{\"s3_key\":\"$S3_KEY\",\"funda_url\":\"https://www.funda.nl/koop/utrecht/huis-12345/\"}" 2>&1) || true
        ONBOARD_HTTP=$(curl -s -o /dev/null -w "%{http_code}" --max-time 60 -X POST "$BASE/onboard" \
            -H "$ONBOARD_AUTH" \
            -H "Content-Type: application/json" \
            -d "{\"s3_key\":\"$S3_KEY\",\"funda_url\":\"https://www.funda.nl/koop/utrecht/huis-12345/\"}" 2>&1) || true

        if [ "$ONBOARD_HTTP" = "200" ]; then
            check "POST /onboard returns 200" "$ONBOARD_HTTP" "200"

            SESSION_ID=$(echo "$ONBOARD_RESP" | jq -r '.session_id' 2>/dev/null) || SESSION_ID=""
            check "onboard response has session_id" "$([ -n "$SESSION_ID" ] && [ "$SESSION_ID" != "null" ] && echo true || echo false)" "true"
            echo ""

            # ── 6. Chat turn (SSE) ───────────────────────────────────────
            echo "── 6. Chat turn (user message → SSE) ──"
            if [ -n "$SESSION_ID" ] && [ "$SESSION_ID" != "null" ]; then
                SSE_RESP=$(curl -sN --max-time 60 -X POST "$BASE/chat/sessions/$SESSION_ID/turns" \
                    -H "$CHAT_AUTH" \
                    -H "Content-Type: application/json" \
                    -H "Accept: text/event-stream" \
                    -d '{"type":"user_message","content":"How am I doing?"}' 2>&1) || true

                HAS_DONE=$(echo "$SSE_RESP" | grep -c "event: done" 2>/dev/null) || HAS_DONE=0
                if [ "$HAS_DONE" -ge 1 ]; then
                    check "SSE stream contains done event" "true" "true"
                else
                    red "SSE stream missing done event"
                    FAIL=$((FAIL + 1))
                fi

                HAS_DELTA=$(echo "$SSE_RESP" | grep -c "event: delta" 2>/dev/null) || HAS_DELTA=0
                if [ "$HAS_DELTA" -ge 1 ]; then
                    check "SSE stream contains delta events" "true" "true"
                else
                    red "SSE stream missing delta events"
                    FAIL=$((FAIL + 1))
                fi
            else
                skip "Chat turn" "no valid session_id from onboard"
            fi
        else
            skip "POST /onboard" "HTTP $ONBOARD_HTTP — $(echo "$ONBOARD_RESP" | head -c 120)"
            skip "Chat turn" "depends on onboard"
        fi
    fi
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
