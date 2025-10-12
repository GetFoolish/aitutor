#!/bin/bash

echo "========================================"
echo "🔍 Teaching Assistant Integration Validator"
echo "========================================"
echo ""

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check counter
checks_passed=0
checks_failed=0

check_file() {
    if [ -f "$1" ]; then
        echo -e "${GREEN}✓${NC} Found: $1"
        ((checks_passed++))
        return 0
    else
        echo -e "${RED}✗${NC} Missing: $1"
        ((checks_failed++))
        return 1
    fi
}

check_content() {
    if grep -q "$2" "$1" 2>/dev/null; then
        echo -e "${GREEN}✓${NC} $3"
        ((checks_passed++))
        return 0
    else
        echo -e "${RED}✗${NC} $3"
        ((checks_failed++))
        return 1
    fi
}

echo "1. Checking Backend Files..."
check_file "$SCRIPT_DIR/backend/ta_server.py"
check_file "$SCRIPT_DIR/backend/teaching_assistant/ta_core.py"
check_file "$SCRIPT_DIR/backend/teaching_assistant/emotional_intelligence.py"
check_file "$SCRIPT_DIR/backend/teaching_assistant/context_provider.py"
check_file "$SCRIPT_DIR/backend/teaching_assistant/performance_tracker.py"
check_file "$SCRIPT_DIR/backend/memory/vector_store.py"
check_file "$SCRIPT_DIR/backend/memory/knowledge_graph.py"
echo ""

echo "2. Checking Frontend Files..."
check_file "$SCRIPT_DIR/frontend/src/lib/teaching-assistant-bridge.ts"
check_file "$SCRIPT_DIR/frontend/src/App.tsx"
echo ""

echo "3. Checking Integration Points..."
check_content "$SCRIPT_DIR/frontend/src/App.tsx" "TeachingAssistantBridge" "App.tsx imports TA Bridge"
check_content "$SCRIPT_DIR/frontend/src/App.tsx" "attachToGeminiClient" "App.tsx attaches bridge to Gemini client"
check_content "$SCRIPT_DIR/backend/ta_server.py" "handle_gemini_response" "TA server handles Gemini responses"
check_content "$SCRIPT_DIR/backend/ta_server.py" "inject_prompt_callback" "TA server has prompt injection callback"
echo ""

echo "4. Checking Model Upgrade..."
check_content "$SCRIPT_DIR/frontend/src/hooks/use-live-api.ts" "gemini-2.5-flash-live" "use-live-api.ts uses new model"
check_content "$SCRIPT_DIR/frontend/src/components/altair/Altair.tsx" "gemini-2.5-flash-live" "Altair.tsx uses new model"
echo ""

echo "5. Checking run_tutor.sh..."
check_content "$SCRIPT_DIR/run_tutor.sh" "ta_server.py" "run_tutor.sh starts TA server"
check_content "$SCRIPT_DIR/run_tutor.sh" "logs/ta_server.log" "run_tutor.sh logs TA server output"
echo ""

echo "6. Testing WebSocket Connectivity..."
if command -v nc &> /dev/null; then
    # Check if TA server port is available (not in use means it's ready to be started)
    if ! nc -z localhost 9000 2>/dev/null; then
        echo -e "${GREEN}✓${NC} Port 9000 available for TA server"
        ((checks_passed++))
    else
        echo -e "${YELLOW}⚠${NC} Port 9000 already in use (TA server might be running)"
        ((checks_passed++))
    fi
else
    echo -e "${YELLOW}⚠${NC} nc command not available, skipping port check"
fi
echo ""

echo "========================================"
echo "Results:"
echo -e "  ${GREEN}Passed: $checks_passed${NC}"
echo -e "  ${RED}Failed: $checks_failed${NC}"
echo "========================================"
echo ""

if [ $checks_failed -eq 0 ]; then
    echo -e "${GREEN}✅ All checks passed!${NC}"
    echo ""
    echo "Next steps to validate the integration:"
    echo "1. Start the system:  ./run_tutor.sh"
    echo "2. Watch TA logs:     tail -f logs/ta_server.log"
    echo "3. Open frontend:     http://localhost:3000"
    echo "4. Start a session and check console for TA messages"
    echo ""
    exit 0
else
    echo -e "${RED}❌ Some checks failed!${NC}"
    echo "Please review the missing files or configurations above."
    exit 1
fi
