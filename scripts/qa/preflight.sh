#!/usr/bin/env bash
#
# Pre-flight QA check entry point
#
# Runs fast automated QA checks using cmux browser before manual testing.
# Catches regressions in < 30s.
#
# Usage:
#   ./scripts/qa/preflight.sh
#
# Environment variables:
#   FRONTEND_URL     Frontend URL (default: http://localhost:5173)
#   DASH_API_URL     Backend API URL (default: http://localhost:8000)
#   QA_ARTIFACTS_DIR Custom artifacts directory (optional)
#

set -e

# Get script and project directories
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Load .env if exists (for MongoDB URI, etc.)
if [[ -f "$PROJECT_ROOT/.env" ]]; then
    # shellcheck source=/dev/null
    set -a
    source "$PROJECT_ROOT/.env"
    set +a
fi

# Activate venv if not already active
if [[ -z "$VIRTUAL_ENV" ]]; then
    if [[ -d "$PROJECT_ROOT/venv" ]]; then
        echo "Activating venv..."
        # shellcheck source=/dev/null
        source "$PROJECT_ROOT/venv/bin/activate"
    elif [[ -d "$PROJECT_ROOT/env" ]]; then
        echo "Activating env..."
        # shellcheck source=/dev/null
        source "$PROJECT_ROOT/env/bin/activate"
    else
        echo -e "${RED}❌ No virtual environment found${NC}"
        echo "   Please create one with: python3 -m venv venv"
        exit 1
    fi
fi

# Set environment variables with defaults
export FRONTEND_URL="${FRONTEND_URL:-http://localhost:5173}"
export DASH_API_URL="${DASH_API_URL:-http://localhost:8000}"

# Create artifacts directory with timestamp
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
if [[ -n "$QA_ARTIFACTS_DIR" ]]; then
    ARTIFACTS_DIR="$QA_ARTIFACTS_DIR"
else
    ARTIFACTS_DIR="$PROJECT_ROOT/artifacts/qa/run-$TIMESTAMP"
fi

mkdir -p "$ARTIFACTS_DIR/screenshots"
mkdir -p "$ARTIFACTS_DIR/dom-snapshots"
mkdir -p "$ARTIFACTS_DIR/logs"

export QA_ARTIFACTS_DIR="$ARTIFACTS_DIR"

# Check if services are running (quick smoke test)
echo "🔍 Checking services..."

if ! curl -sf "$FRONTEND_URL" > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Frontend not responding at $FRONTEND_URL${NC}"
    echo "   Start services with: ./run_tutor.sh"
    exit 1
fi

if ! curl -sf "$DASH_API_URL/health" > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Backend not responding at $DASH_API_URL${NC}"
    echo "   Start services with: ./run_tutor.sh"
    exit 1
fi

echo -e "${GREEN}✅ Services are running${NC}"
echo ""

# Check cmux browser availability
if ! command -v cmux &> /dev/null; then
    echo -e "${RED}❌ cmux browser not found in PATH${NC}"
    echo "   Install cmux to use browser automation checks"
    exit 1
fi

# Print configuration
echo "📋 Configuration:"
echo "   Frontend URL: $FRONTEND_URL"
echo "   Backend URL:  $DASH_API_URL"
echo "   Artifacts:    $ARTIFACTS_DIR"
echo ""

# Run QA checks
echo "🚀 Running Pre-Flight QA Checks..."
echo ""

# Change to project root for consistent imports
cd "$PROJECT_ROOT"

# Run qa_runner.py
if python3 "$SCRIPT_DIR/qa_runner.py" --artifacts-dir "$ARTIFACTS_DIR"; then
    echo -e "${GREEN}✅ All QA checks passed${NC}"
    exit 0
else
    echo -e "${RED}❌ QA checks failed - review artifacts${NC}"
    echo "   Artifacts: $ARTIFACTS_DIR"
    exit 1
fi
