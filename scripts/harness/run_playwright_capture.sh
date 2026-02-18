#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SCREENSHOT_DIR_INPUT="${1:-}"
SCREENSHOT_DIR="${SCREENSHOT_DIR_INPUT:-${HARNESS_SCREENSHOT_DIR:-$ROOT/artifacts/harness/screenshots}}"
AUTO_START="${HARNESS_AUTO_START:-0}"
SKIP_WEBSOCKET="${HARNESS_SKIP_WEBSOCKET:-0}"

RUN_TUTOR_PID=""
RUN_TUTOR_LOG="$ROOT/artifacts/harness/run_tutor_for_playwright.log"

if [[ "$SCREENSHOT_DIR" != /* ]]; then
  SCREENSHOT_DIR="$ROOT/$SCREENSHOT_DIR"
fi

cleanup() {
  if [[ -n "$RUN_TUTOR_PID" ]]; then
    kill "$RUN_TUTOR_PID" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

detect_frontend_port() {
  local vite_cfg="$ROOT/frontend/vite.config.ts"
  if [[ -f "$vite_cfg" ]]; then
    local port
    port="$(grep -Eo 'port[[:space:]]*:[[:space:]]*[0-9]+' "$vite_cfg" | head -n 1 | grep -Eo '[0-9]+' || true)"
    if [[ -n "$port" ]]; then
      echo "$port"
      return 0
    fi
  fi
  echo "3000"
}

if [[ -n "${PLAYWRIGHT_BASE_URL:-}" ]]; then
  BASE_URL="$PLAYWRIGHT_BASE_URL"
else
  BASE_URL="http://localhost:$(detect_frontend_port)"
fi

wait_http_ok() {
  local url="$1"
  local timeout_s="${2:-120}"
  local start
  start=$(date +%s)
  while true; do
    if curl -fsS "$url" >/dev/null 2>&1; then
      return 0
    fi
    if (( $(date +%s) - start > timeout_s )); then
      return 1
    fi
    sleep 2
  done
}

ensure_up() {
  local url="$1"
  local timeout_s="${2:-120}"
  if wait_http_ok "$url" 5; then
    return 0
  fi

  if [[ "$AUTO_START" == "1" ]]; then
    if [[ -z "$RUN_TUTOR_PID" ]]; then
      mkdir -p "$(dirname "$RUN_TUTOR_LOG")"
      (cd "$ROOT" && bash "$ROOT/run_tutor.sh") >"$RUN_TUTOR_LOG" 2>&1 &
      RUN_TUTOR_PID="$!"
    fi
    wait_http_ok "$url" "$timeout_s"
    return 0
  fi

  echo "Service unavailable at $url"
  echo "Tip: start services first or set HARNESS_AUTO_START=1"
  return 1
}

mkdir -p "$SCREENSHOT_DIR"

ensure_up "${AUTH_BASE:-http://localhost:8003}/health" 120
ensure_up "${DASH_BASE:-http://localhost:8000}/health" 180
if [[ "$SKIP_WEBSOCKET" != "1" && "$SKIP_WEBSOCKET" != "true" ]]; then
  ensure_up "${TA_BASE:-http://localhost:8002}/health" 120
fi

resolve_frontend_base_url() {
  local detected="http://localhost:$(detect_frontend_port)"
  local candidates=("$BASE_URL" "$detected" "http://localhost:3000" "http://localhost:5173")
  local seen=""
  local c
  for c in "${candidates[@]}"; do
    [[ -z "$c" ]] && continue
    case ",$seen," in
      *",$c,"*) continue ;;
    esac
    seen="${seen},$c"
    if wait_http_ok "$c/app/dev-login" 3; then
      BASE_URL="$c"
      return 0
    fi
  done
  return 1
}

if ! resolve_frontend_base_url; then
  ensure_up "$BASE_URL/app/dev-login" 180
fi

# Best effort browser install. If this fails, test command may still work if browser already installed.
if command -v npx >/dev/null 2>&1; then
  npx --yes @playwright/test install chromium >/dev/null 2>&1 || true
else
  echo "npx is required to run Playwright harness"
  exit 1
fi

cd "$ROOT/frontend"
HARNESS_SCREENSHOT_DIR="$SCREENSHOT_DIR" \
PLAYWRIGHT_BASE_URL="$BASE_URL" \
npx --yes @playwright/test test -c playwright.harness.config.ts --reporter=line

echo "$SCREENSHOT_DIR"
