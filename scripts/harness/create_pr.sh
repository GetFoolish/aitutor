#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

RUN_HARNESS="${RUN_HARNESS_BEFORE_PR:-1}"
STAMP="$(date -u +%Y%m%d-%H%M%S)"
BRANCH="codex/content-pipeline-harness-${STAMP}"

if [[ "$RUN_HARNESS" == "1" ]]; then
  python3 scripts/harness/run_pipeline_harness.py --mode local
fi

LATEST_RUN_DIR="$(ls -dt artifacts/harness/run-* 2>/dev/null | head -n 1 || true)"
if [[ -z "$LATEST_RUN_DIR" ]]; then
  echo "No harness run artifacts found under artifacts/harness/run-*"
  exit 1
fi

PR_BODY="$LATEST_RUN_DIR/PR_PACKET.md"
if [[ ! -f "$PR_BODY" ]]; then
  echo "PR packet not found: $PR_BODY"
  exit 1
fi

git checkout -b "$BRANCH"
git add .github/workflows/content-pipeline-harness.yml \
        .github/PULL_REQUEST_TEMPLATE.md \
        docs/harness/CONTENT_PIPELINE_HARNESS.md \
        scripts/harness \
        frontend/playwright.harness.config.ts \
        frontend/e2e/content_pipeline_harness.spec.ts

git commit -m "Add content pipeline delivery harness with PR gates"
git push -u origin "$BRANCH"

gh pr create \
  --title "Add content pipeline harness and PR quality gates" \
  --body-file "$PR_BODY"
