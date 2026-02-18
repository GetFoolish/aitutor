#!/bin/zsh
set -u

TOKEN_FILE="artifacts/pretest/token.txt"
SUBJECTS_FILE="artifacts/pretest/all_subjects.txt"
OUT_DIR="artifacts/pretest"
STAMP=$(date +%Y%m%d-%H%M%S)
JSONL="$OUT_DIR/full_sweep_${STAMP}.jsonl"
SUMMARY_JSON="$OUT_DIR/full_sweep_${STAMP}.json"

AUTH_TOKEN=$(cat "$TOKEN_FILE")
: > "$JSONL"

while IFS= read -r SUBJECT; do
  [ -z "$SUBJECT" ] && continue
  SAFE=$(echo "$SUBJECT" | tr '[:upper:]' '[:lower:]' | tr -cs 'a-z0-9' '_' | sed 's/^_//;s/_$//')

  START_FILE="$OUT_DIR/start_full_${STAMP}_${SAFE}.json"
  Q_FILE="$OUT_DIR/questions_full_${STAMP}_${SAFE}.json"

  PAYLOAD=$(jq -nc --arg s "$SUBJECT" --arg r "US" '{subject:$s,region:$r}')

  t0=$(date +%s)
  START_CODE=$(curl -sS --retry 1 --retry-delay 1 -m 45 \
    -o "$START_FILE" -w "%{http_code}" \
    -H "Authorization: Bearer $AUTH_TOKEN" \
    -H "Content-Type: application/json" \
    -d "$PAYLOAD" \
    http://localhost:8000/api/start-subject)
  rc_start=$?
  t1=$(date +%s)

  Q_CODE=$(curl -sS --retry 1 --retry-delay 1 -m 120 \
    -o "$Q_FILE" -w "%{http_code}" \
    -H "Authorization: Bearer $AUTH_TOKEN" \
    http://localhost:8000/api/questions/5)
  rc_q=$?
  t2=$(date +%s)

  if [ $rc_start -ne 0 ]; then START_CODE=0; fi
  if [ $rc_q -ne 0 ]; then Q_CODE=0; fi

  START_SEC=$((t1 - t0))
  Q_SEC=$((t2 - t1))

  Q_COUNT=$(jq 'if type=="array" then length else 0 end' "$Q_FILE" 2>/dev/null || echo 0)
  SKILLS_COUNT=$(jq '.skills_count // 0' "$START_FILE" 2>/dev/null || echo 0)
  STATUS=$(jq -r '.status // "unknown"' "$START_FILE" 2>/dev/null || echo "unknown")

  jq -nc \
    --arg subject "$SUBJECT" \
    --arg status "$STATUS" \
    --argjson start_code "$START_CODE" \
    --argjson questions_code "$Q_CODE" \
    --argjson skills_count "$SKILLS_COUNT" \
    --argjson questions_count "$Q_COUNT" \
    --argjson start_seconds "$START_SEC" \
    --argjson questions_seconds "$Q_SEC" \
    '{subject:$subject,status:$status,start_code:$start_code,questions_code:$questions_code,skills_count:$skills_count,questions_count:$questions_count,start_seconds:$start_seconds,questions_seconds:$questions_seconds}' \
    >> "$JSONL"

done < "$SUBJECTS_FILE"

jq -s . "$JSONL" > "$SUMMARY_JSON"
echo "$SUMMARY_JSON"
