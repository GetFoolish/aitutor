#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$SCRIPT_DIR/logs"

load_env_file() {
    local env_path="$1"
    if [[ ! -f "$env_path" ]]; then
        return
    fi

    echo "Loading environment variables from $(basename "$env_path")..."
    while IFS='=' read -r key value; do
        [[ -z "$key" ]] && continue
        [[ $key =~ ^[[:space:]]*# ]] && continue
        key="$(echo "$key" | sed 's/^[[:space:]]*//' | sed 's/[[:space:]]*$//')"
        value="$(echo "$value" | sed 's/^"//' | sed 's/"$//' | sed "s/^'//" | sed "s/'$//")"
        export "$key=$value"
    done < "$env_path"
}

find_python_bin() {
    if [[ -n "${VIRTUAL_ENV:-}" ]]; then
        if [[ -x "$VIRTUAL_ENV/bin/python3" ]]; then
            echo "$VIRTUAL_ENV/bin/python3"
            return
        fi
        if [[ -x "$VIRTUAL_ENV/bin/python" ]]; then
            echo "$VIRTUAL_ENV/bin/python"
            return
        fi
    fi

    if [[ -d "$SCRIPT_DIR/.venv" ]]; then
        echo "$SCRIPT_DIR/.venv/bin/python3"
        return
    fi

    if [[ -d "$SCRIPT_DIR/env" ]]; then
        echo "$SCRIPT_DIR/env/bin/python3"
        return
    fi

    echo ""
}

validate_required_env() {
    local missing=()
    local required_vars=(
        MONGODB_URI
        OPENROUTER_API_KEY
        GEMINI_API_KEY
        JWT_SECRET
        GOOGLE_CLIENT_ID
        GOOGLE_CLIENT_SECRET
        OBSERVER_API_KEY
    )

    for var_name in "${required_vars[@]}"; do
        if [[ -z "${!var_name:-}" ]]; then
            missing+=("$var_name")
        fi
    done

    if [[ ${#missing[@]} -gt 0 ]]; then
        echo "❌ Missing required environment variables:"
        printf '   - %s\n' "${missing[@]}"
        echo ""
        echo "Run ./setup-local-env.sh and fill in the placeholders before starting the app."
        exit 1
    fi

    local placeholder_vars=()
    local placeholder_prefixes=(
        "replace-with-"
        "CHANGE_ME_"
    )

    for var_name in "${required_vars[@]}"; do
        local value="${!var_name:-}"
        for prefix in "${placeholder_prefixes[@]}"; do
            if [[ "$value" == "$prefix"* ]]; then
                placeholder_vars+=("$var_name")
                break
            fi
        done
    done

    if [[ ${#placeholder_vars[@]} -gt 0 ]]; then
        echo "❌ Replace placeholder values before starting the app:"
        printf '   - %s\n' "${placeholder_vars[@]}"
        echo ""
        echo "Run ./setup-local-env.sh if needed, then edit .env with real credentials."
        exit 1
    fi
}

wait_for_service() {
    local name="$1"
    local url="$2"
    local ready_substring="${3:-}"
    local max_wait="${4:-60}"

    echo "Waiting for $name..."
    for ((attempt = 1; attempt <= max_wait; attempt++)); do
        local response
        response="$(curl -sS "$url" 2>/dev/null || true)"

        if [[ -n "$response" ]]; then
            if [[ -z "$ready_substring" || "$response" == *"$ready_substring"* ]]; then
                echo "  $name is ready"
                return 0
            fi
        fi

        sleep 1
    done

    echo "❌ Timed out waiting for $name at $url"
    echo "Inspect logs in $LOG_DIR for details."
    exit 1
}

load_env_file "$SCRIPT_DIR/.env"

PYTHON_BIN="$(find_python_bin)"
if [[ -z "$PYTHON_BIN" || ! -x "$PYTHON_BIN" ]]; then
    echo "❌ No project virtual environment found."
    echo "Create one with:"
    echo "  python3 -m venv .venv"
    echo "  source .venv/bin/activate"
    echo "  pip install -r requirements.txt -r requirements-test.txt"
    echo "  cd frontend && npm install && cd .."
    exit 1
fi

if [[ ! -d "$SCRIPT_DIR/frontend/node_modules" ]]; then
    echo "❌ Frontend dependencies are missing."
    echo "Install them with:"
    echo "  cd frontend && npm install"
    exit 1
fi

validate_required_env

rm -rf "$LOG_DIR"
mkdir -p "$LOG_DIR"

export FRONTEND_URL="${FRONTEND_URL:-http://localhost:3000}"
export DASH_API_URL="${DASH_API_URL:-http://localhost:8000}"
export SHERLOCKED_API_URL="${SHERLOCKED_API_URL:-http://localhost:8001}"
export TEACHING_ASSISTANT_API_URL="${TEACHING_ASSISTANT_API_URL:-http://localhost:8002}"
export AUTH_SERVICE_URL="${AUTH_SERVICE_URL:-http://localhost:8003}"
export ALLOWED_ORIGINS="${ALLOWED_ORIGINS:-http://localhost:3000}"
export VITE_DASH_API_URL="${VITE_DASH_API_URL:-$DASH_API_URL}"
export VITE_SHERLOCKED_API_URL="${VITE_SHERLOCKED_API_URL:-$SHERLOCKED_API_URL}"
export VITE_TEACHING_ASSISTANT_API_URL="${VITE_TEACHING_ASSISTANT_API_URL:-$TEACHING_ASSISTANT_API_URL}"
export VITE_AUTH_SERVICE_URL="${VITE_AUTH_SERVICE_URL:-$AUTH_SERVICE_URL}"
export VITE_GOOGLE_CLIENT_ID="${VITE_GOOGLE_CLIENT_ID:-$GOOGLE_CLIENT_ID}"

pids=()

cleanup() {
    echo "Shutting down AI Tutor..."
    for pid in "${pids[@]}"; do
        kill "$pid" 2>/dev/null || true
    done
}

trap cleanup INT TERM EXIT

echo "Using Python: $PYTHON_BIN"

echo "Starting DASH API... logs/dash_api.log"
(cd "$SCRIPT_DIR" && "$PYTHON_BIN" services/DashSystem/dash_api.py) > "$LOG_DIR/dash_api.log" 2>&1 &
pids+=($!)

echo "Starting SherlockED API... logs/sherlocked_exam.log"
(cd "$SCRIPT_DIR" && "$PYTHON_BIN" services/SherlockEDApi/run_backend.py) > "$LOG_DIR/sherlocked_exam.log" 2>&1 &
pids+=($!)

echo "Starting TeachingAssistant API... logs/teaching_assistant.log"
(cd "$SCRIPT_DIR" && "$PYTHON_BIN" services/TeachingAssistant/api.py) > "$LOG_DIR/teaching_assistant.log" 2>&1 &
pids+=($!)

echo "Starting Auth Service... logs/auth_service.log"
(cd "$SCRIPT_DIR" && "$PYTHON_BIN" services/AuthService/auth_api.py) > "$LOG_DIR/auth_service.log" 2>&1 &
pids+=($!)

wait_for_service "DASH API" "$DASH_API_URL/health" '"ready":true' 90
wait_for_service "SherlockED API" "$SHERLOCKED_API_URL/health"
wait_for_service "TeachingAssistant API" "$TEACHING_ASSISTANT_API_URL/health"
wait_for_service "Auth Service" "$AUTH_SERVICE_URL/health"

echo "Starting frontend... logs/frontend.log"
(cd "$SCRIPT_DIR/frontend" && npm run dev -- --host 0.0.0.0) > "$LOG_DIR/frontend.log" 2>&1 &
pids+=($!)

echo ""
echo "AI Tutor is starting."
echo "  Frontend:           http://localhost:3000"
echo "  DASH API:           http://localhost:8000"
echo "  SherlockED API:     http://localhost:8001"
echo "  TeachingAssistant:  http://localhost:8002"
echo "  Auth Service:       http://localhost:8003"
echo ""
echo "Legacy note: services/Tutor is not started by this script."
echo "Press Ctrl+C to stop everything."

wait
