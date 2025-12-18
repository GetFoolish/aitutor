#!/usr/bin/env bash

# ==============================================================================
# Athena Renderer Test Script
# ==============================================================================
# Quick launcher for testing the new Athena rendering engine
# This starts only the services needed for Athena testing:
# - sherlockedAPI_New (Athena backend on port 8010)
# - Frontend (React app on port 3000)
# ==============================================================================

set -e  # Exit on error

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║         Athena Renderer Test Environment Launcher         ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Load environment variables from .env file if it exists
if [[ -f ".env" ]]; then
    echo -e "${GREEN}✓${NC} Loading environment variables from .env file..."
    # Read .env file and export variables
    while IFS='=' read -r key value; do
        # Skip comments and empty lines
        [[ $key =~ ^[[:space:]]*#.*$ ]] && continue
        [[ -z "$key" ]] && continue
        # Remove leading/trailing whitespace
        key=$(echo "$key" | sed 's/^[[:space:]]*//' | sed 's/[[:space:]]*$//')
        # Remove quotes from value if present
        value=$(echo "$value" | sed 's/^"//' | sed 's/"$//' | sed "s/^'//" | sed "s/'$//")
        # Export the variable
        export "$key=$value"
    done < .env
else
    echo -e "${YELLOW}⚠${NC}  No .env file found. Create one with MongoDB credentials."
    exit 1
fi

# Clean up old logs and create a fresh logs directory
rm -rf "$SCRIPT_DIR/logs/athena"
mkdir -p "$SCRIPT_DIR/logs/athena"

# Detect Python environment
if [[ -z "$VIRTUAL_ENV" ]]; then
    # Not already in a virtual environment - try to find one
    if [[ -d "$SCRIPT_DIR/venv" ]]; then
        echo -e "${GREEN}✓${NC} Activating virtual environment (venv)..."
        source "$SCRIPT_DIR/venv/bin/activate"
    elif [[ -d "$SCRIPT_DIR/env" ]]; then
        echo -e "${GREEN}✓${NC} Activating virtual environment (env)..."
        source "$SCRIPT_DIR/env/bin/activate"
    elif [[ -d "$SCRIPT_DIR/.env" ]]; then
        echo -e "${GREEN}✓${NC} Activating virtual environment (.env)..."
        source "$SCRIPT_DIR/.env/bin/activate"
    else
        echo -e "${YELLOW}⚠${NC}  No virtual environment found - using system Python"
        echo "  (If you encounter issues, create one with: python3 -m venv venv)"
    fi
else
    echo -e "${GREEN}✓${NC} Using already active virtual environment: $VIRTUAL_ENV"
fi

# Get Python executable
if [[ -n "$VIRTUAL_ENV" ]]; then
    if [[ -f "$VIRTUAL_ENV/bin/python3" ]]; then
        PYTHON_BIN="$VIRTUAL_ENV/bin/python3"
    elif [[ -f "$VIRTUAL_ENV/bin/python" ]]; then
        PYTHON_BIN="$VIRTUAL_ENV/bin/python"
    else
        PYTHON_BIN="$(command -v python3 || command -v python)"
    fi
else
    PYTHON_BIN="$(command -v python3 || command -v python)"
fi

echo -e "${GREEN}✓${NC} Using Python: $PYTHON_BIN"

# Array to hold the PIDs of background processes
pids=()

# Function to clean up background processes
cleanup() {
    echo ""
    echo -e "${YELLOW}Shutting down Athena test environment...${NC}"
    for pid in "${pids[@]}"; do
        echo "  Killing process $pid"
        kill "$pid" 2>/dev/null || true
    done
    echo -e "${GREEN}✓${NC} All processes terminated."
    exit 0
}

# Trap the INT signal (sent by Ctrl+C) to run the cleanup function
trap cleanup INT TERM

echo ""
echo -e "${BLUE}Starting services...${NC}"
echo ""

# Start the NEW Athena Backend API (sherlockedAPI_New on port 8010)
echo -e "${GREEN}►${NC} Starting Athena Backend API (port 8010)..."
echo "  Logs → logs/athena/backend.log"
(cd "$SCRIPT_DIR/services/sherlockedAPI_New" && "$PYTHON_BIN" run_backend.py) > "$SCRIPT_DIR/logs/athena/backend.log" 2>&1 &
pids+=($!)

# Give backend a moment to start
sleep 3

# Check if backend is running
if curl -s "http://localhost:8010/health" 2>/dev/null | grep -q "healthy"; then
    echo -e "${GREEN}  ✓ Backend API is running${NC}"
else
    echo -e "${YELLOW}  ⚠ Backend API may still be starting...${NC}"
fi

# Start the Frontend
echo -e "${GREEN}►${NC} Starting Frontend (port 3000)..."
echo "  Logs → logs/athena/frontend.log"
(cd "$SCRIPT_DIR/frontend" && npm run dev) > "$SCRIPT_DIR/logs/athena/frontend.log" 2>&1 &
pids+=($!)

# Give frontend a moment to start
sleep 5

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                  🚀 Athena is Ready!                       ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}📡 Service URLs:${NC}"
echo ""
echo -e "  🆕 ${GREEN}Athena Renderer:${NC}"
echo -e "     http://localhost:3000/app?renderer=athena"
echo ""
echo -e "  📊 ${BLUE}Compare with Perseus:${NC}"
echo -e "     http://localhost:3000/app?renderer=perseus"
echo ""
echo -e "  🔧 ${BLUE}Backend API Health:${NC}"
echo -e "     http://localhost:8010/health"
echo ""
echo -e "  📁 ${BLUE}API Questions:${NC}"
echo -e "     http://localhost:8010/api/questions"
echo ""
echo -e "${YELLOW}📝 Logs:${NC}"
echo "  Backend:  tail -f logs/athena/backend.log"
echo "  Frontend: tail -f logs/athena/frontend.log"
echo ""
echo -e "${YELLOW}⌨️  Keyboard Shortcuts (in browser):${NC}"
echo "  1-4:    Select answer options"
echo "  Enter:  Submit answer / Next question"
echo "  ←/→:    Previous/Next question"
echo ""
echo -e "${RED}Press Ctrl+C to stop all services${NC}"
echo ""

# Show running processes
echo -e "${BLUE}Running PIDs:${NC} ${pids[*]}"
echo ""

# Wait indefinitely until the script is interrupted
wait
