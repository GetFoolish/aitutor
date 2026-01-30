#!/usr/bin/env bash
set -euo pipefail

TA_URL="${TEACHING_ASSISTANT_URL:-http://localhost:8002}"
JWT_SECRET="${JWT_SECRET:-}"

if [[ -z "$JWT_SECRET" ]]; then
  if [[ -f ".env" ]]; then
    JWT_SECRET=$(rg -n "^JWT_SECRET=" -m 1 .env | cut -d= -f2- || true)
  fi
fi

if [[ -z "$JWT_SECRET" ]]; then
  echo "ERROR: JWT_SECRET not set and .env not found."
  echo "Set it with: export JWT_SECRET='your-secret'"
  exit 1
fi

export JWT_SECRET

PY_BIN="${PY_BIN:-./.venv/bin/python}"
if [[ ! -x "$PY_BIN" ]]; then
  echo "ERROR: Python not found at $PY_BIN"
  echo "Set it with: export PY_BIN=/path/to/python"
  exit 1
fi

AUTH_TOKEN=$("$PY_BIN" - <<'PY'
import os
from services.AuthService import jwt_utils
print(jwt_utils.create_jwt_token({
    "user_id": "test_user_123",
    "email": "test@example.com",
    "name": "Test User",
    "google_id": "google_123"
}))
PY
)

JQ_BIN=$(command -v jq || true)

echo "== Start session =="
START_RESP=$(curl -s --max-time 30 -X POST "$TA_URL/session/start" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -d '{}')

if [[ -n "$JQ_BIN" ]]; then
  SESSION_ID=$(echo "$START_RESP" | jq -r .session_info.session_id)
else
  SESSION_ID=$("$PY_BIN" - <<'PY'
import json, sys
data=json.loads(sys.stdin.read())
print(data["session_info"]["session_id"])
PY
<<<"$START_RESP")
fi

if [[ -z "$SESSION_ID" || "$SESSION_ID" == "null" ]]; then
  echo "ERROR: session_id missing in response."
  exit 1
fi

echo "== Send transcript (user memory) =="
curl -s --max-time 20 -X POST "$TA_URL/webhook/feed" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -d '{
    "type":"transcript",
    "timestamp":"2026-01-30T20:10:00Z",
    "data":{
      "session_id":"'"$SESSION_ID"'",
      "transcript":[
        {"speaker":"user","text":"I love astronomy and I am learning fractions.","emotion":"happy"},
        {"speaker":"tutor","text":"Awesome! We can use space examples.","emotion":"encouraging"}
      ]
    }
  }' >/dev/null

echo "== End session (triggers memory extraction) =="
curl -s --max-time 30 -X POST "$TA_URL/session/end" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -d '{}' >/dev/null

echo "== Search memories =="
SEARCH_RESP=$(curl -s --max-time 20 -X POST "$TA_URL/memory/search" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -d '{"query":"astronomy","top_k":5}')

if [[ -n "$JQ_BIN" ]]; then
  echo "$SEARCH_RESP" | jq .
else
  echo "$SEARCH_RESP"
fi

echo "== Done =="
