#!/bin/zsh
set -u
AUTH_TOKEN=$(cat "artifacts/pretest/token.txt")
SUMMARY="artifacts/pretest/fetch_summary.jsonl"
: > "$SUMMARY"
while IFS= read -r SUBJECT; do
  [ -z "$SUBJECT" ] && continue
  SAFE=$(echo "$SUBJECT" | tr "[:upper:]" "[:lower:]" | tr -cs "a-z0-9" "_" | sed "s/^_//;s/_$//")
  PAYLOAD=$(jq -nc --arg s "$SUBJECT" --arg r "US" '{subject:$s,region:$r}')
  START_CODE=$(curl -sS -o "artifacts/pretest/start_${SAFE}.json" -w "%{http_code}" -H "Authorization: Bearer $AUTH_TOKEN" -H "Content-Type: application/json" -d "$PAYLOAD" http://localhost:8000/api/start-subject || echo 000)
  Q_CODE=$(curl -sS -o "artifacts/pretest/questions_${SAFE}.json" -w "%{http_code}" -H "Authorization: Bearer $AUTH_TOKEN" http://localhost:8000/api/questions/10 || echo 000)
  Q_COUNT=$(jq 'if type=="array" then length else 0 end' "artifacts/pretest/questions_${SAFE}.json" 2>/dev/null || echo 0)
  jq -nc --arg s "$SUBJECT" --argjson sc "$START_CODE" --argjson qc "$Q_CODE" --argjson qn "$Q_COUNT" '{subject:$s,start_code:$sc,questions_code:$qc,questions_count:$qn}' >> "$SUMMARY"
done < "artifacts/pretest/subjects.txt"
jq -s . "$SUMMARY" > "artifacts/pretest/fetch_summary.json"
cat "artifacts/pretest/fetch_summary.json"
