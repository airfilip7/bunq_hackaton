#!/usr/bin/env bash
# stream_chat.sh — Call chat endpoint and print final concatenated text.
# Usage:
#   ./scripts/stream_chat.sh <session_id> "How am I doing?"

BASE="${BASE_URL:-http://localhost:8000}"
SESSION_ID="${1:-}"
MSG="${2:-How am I doing?}"

if [ -z "$SESSION_ID" ]; then
  echo "Usage: $0 <session_id> [message]"
  exit 1
fi

curl -sN -X POST "$BASE/chat/sessions/$SESSION_ID/turns" \
  -H "Authorization: Bearer demo" \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d "{\"type\":\"user_message\",\"content\":\"$MSG\"}" | \
python3 -c "
import sys, json
text = ''
tool_calls = []
tool_results = []
proposal = None
error = None

for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    if line.startswith('event:'):
        event = line[6:].strip()
        continue
    if line.startswith('data:'):
        try:
            d = json.loads(line[5:].strip())
        except:
            continue
        if event == 'delta' and 'text' in d:
            text += d['text']
        elif event == 'tool_call':
            tool_calls.append(d)
        elif event == 'tool_result':
            tool_results.append(d)
        elif event == 'tool_proposal':
            proposal = d
        elif event == 'error':
            error = d.get('message', str(d))

print('=' * 60)
if error:
    print('ERROR:', error)
if tool_calls:
    print('TOOLS CALLED:')
    for tc in tool_calls:
        print(f\"  - {tc.get('name', 'unknown')}\")
if tool_results:
    print('TOOL RESULTS:')
    for tr in tool_results:
        status = 'OK' if tr.get('ok') else 'FAIL'
        print(f\"  - {tr.get('name', 'unknown')}: {status}\")
if proposal:
    print('PENDING PROPOSAL:')
    print(f\"  tool: {proposal.get('tool_name')}\")
    print(f\"  amount: {proposal.get('params', {}).get('amount_eur', 'N/A')} EUR\")
    print(f\"  risk: {proposal.get('risk_level')}\")
print('=' * 60)
print()
print(text)
"
