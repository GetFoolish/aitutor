#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OUT_REL="${1:-artifacts/harness/greptile.json}"
if [[ "$OUT_REL" = /* ]]; then
  OUT_PATH="$OUT_REL"
else
  OUT_PATH="$ROOT/$OUT_REL"
fi
REQUIRE="${HARNESS_REQUIRE_GREPTILE:-0}"
CMD="${GREPTILE_REVIEW_COMMAND:-}"

mkdir -p "$(dirname "$OUT_PATH")"

if [[ -z "$CMD" ]]; then
  cat > "$OUT_PATH" <<JSON
{
  "ok": false,
  "skipped": true,
  "reason": "GREPTILE_REVIEW_COMMAND not set"
}
JSON
  if [[ "$REQUIRE" == "1" ]]; then
    echo "Greptile gate required but GREPTILE_REVIEW_COMMAND is not configured"
    exit 1
  fi
  exit 0
fi

if [[ "$REQUIRE" == "1" && -z "${GREPTILE_API_KEY:-}" ]]; then
  cat > "$OUT_PATH" <<JSON
{
  "ok": false,
  "skipped": false,
  "required": true,
  "reason": "GREPTILE_API_KEY not set"
}
JSON
  echo "Greptile gate required but GREPTILE_API_KEY is not configured"
  exit 1
fi

STDOUT_PATH="${OUT_PATH%.json}.stdout.log"
STDERR_PATH="${OUT_PATH%.json}.stderr.log"

set +e
/bin/zsh -lc "$CMD" >"$STDOUT_PATH" 2>"$STDERR_PATH"
RC=$?
set -e

OK="false"
if [[ $RC -eq 0 ]]; then
  OK="true"
fi

DISPLAY_CMD="$CMD"
if [[ -n "${GREPTILE_API_KEY:-}" ]]; then
  DISPLAY_CMD="${DISPLAY_CMD//${GREPTILE_API_KEY}/***REDACTED***}"
fi
DISPLAY_CMD="$(printf '%s' "$DISPLAY_CMD" | tr '\n\r' '  ')"
ESCAPED_CMD="${DISPLAY_CMD//\\/\\\\}"
ESCAPED_CMD="${ESCAPED_CMD//\"/\\\"}"

cat > "$OUT_PATH" <<JSON
{
  "ok": $OK,
  "skipped": false,
  "required": $([[ "$REQUIRE" == "1" ]] && echo true || echo false),
  "command": "$ESCAPED_CMD",
  "returncode": $RC,
  "stdout": "${STDOUT_PATH#$ROOT/}",
  "stderr": "${STDERR_PATH#$ROOT/}"
}
JSON

if [[ "$REQUIRE" == "1" && $RC -ne 0 ]]; then
  exit 1
fi

exit 0
