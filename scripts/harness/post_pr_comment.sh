#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PR_NUMBER="${1:-${PR_NUMBER:-}}"
BODY_FILE="${2:-${PR_BODY_FILE:-}}"

if [[ -z "$PR_NUMBER" ]]; then
  echo "PR number is required (arg1 or PR_NUMBER env)"
  exit 1
fi

if [[ -z "$BODY_FILE" ]]; then
  echo "PR body file is required (arg2 or PR_BODY_FILE env)"
  exit 1
fi

if [[ ! -f "$BODY_FILE" ]]; then
  echo "Body file not found: $BODY_FILE"
  exit 1
fi

cd "$ROOT"
gh pr comment "$PR_NUMBER" --body-file "$BODY_FILE"
