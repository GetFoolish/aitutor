#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_TEMPLATE="$SCRIPT_DIR/.env.example"
ENV_FILE="$SCRIPT_DIR/.env"

if [[ ! -f "$ENV_TEMPLATE" ]]; then
    echo "❌ Missing .env.example template"
    exit 1
fi

echo "🚀 Setting up local environment contract..."

if [[ -f "$ENV_FILE" ]]; then
    backup_path="$ENV_FILE.backup.$(date +%Y%m%d%H%M%S)"
    cp "$ENV_FILE" "$backup_path"
    echo "⚠️  Existing .env backed up to $backup_path"
fi

cp "$ENV_TEMPLATE" "$ENV_FILE"

python3 - <<'PY' "$ENV_FILE"
import secrets
import sys
from pathlib import Path

env_path = Path(sys.argv[1])
content = env_path.read_text()
content = content.replace("CHANGE_ME_GENERATED_ON_SETUP", secrets.token_urlsafe(32), 1)
content = content.replace("CHANGE_ME_GENERATED_ON_SETUP", secrets.token_urlsafe(24), 1)
env_path.write_text(content)
PY

echo "✅ Wrote .env from .env.example"
echo ""
echo "Next steps:"
echo "  1. Review .env and replace placeholder API credentials."
echo "  2. Create a virtual environment: python3 -m venv .venv"
echo "  3. Activate it: source .venv/bin/activate"
echo "  4. Install backend deps: pip install -r requirements.txt -r requirements-test.txt"
echo "  5. Install frontend deps: cd frontend && npm install && cd .."
echo "  6. Start the app: ./run_tutor.sh"
