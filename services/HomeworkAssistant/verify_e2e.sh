#!/bin/bash

# E2E Verification Script for Homework Feature
# This script verifies the automated/programmatic parts of the E2E flow

echo "================================================"
echo "E2E Verification: Homework Upload & AI Feature"
echo "================================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track results
PASSED=0
FAILED=0
WARNINGS=0

# Helper function for test results
pass() {
    echo -e "${GREEN}✓${NC} $1"
    ((PASSED++))
}

fail() {
    echo -e "${RED}✗${NC} $1"
    ((FAILED++))
}

warn() {
    echo -e "${YELLOW}⚠${NC} $1"
    ((WARNINGS++))
}

echo "Step 1: Verify Backend Service (Port 8004)"
echo "-------------------------------------------"

# Check if port 8004 is listening
if lsof -Pi :8004 -sTCP:LISTEN -t >/dev/null 2>&1; then
    pass "Port 8004 is listening"
else
    fail "Port 8004 is not listening - HomeworkAssistant not running"
    echo "   Run: cd services/HomeworkAssistant && python -m uvicorn api:app --port 8004 --reload"
fi

# Check health endpoint
HEALTH_RESPONSE=$(curl -s http://localhost:8004/health)
if echo "$HEALTH_RESPONSE" | grep -q "HomeworkAssistant"; then
    pass "Health endpoint returns correct service name"
else
    fail "Health endpoint not responding correctly"
    echo "   Response: $HEALTH_RESPONSE"
fi

echo ""
echo "Step 2: Verify Frontend Service (Port 3000)"
echo "-------------------------------------------"

# Check if port 3000 is listening
if lsof -Pi :3000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    pass "Port 3000 is listening"
else
    fail "Port 3000 is not listening - Frontend not running"
    echo "   Run: cd frontend && npm run dev"
fi

# Check if frontend is responding
FRONTEND_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000 2>/dev/null)
if [ "$FRONTEND_STATUS" = "200" ]; then
    pass "Frontend is responding (HTTP 200)"
else
    warn "Frontend returned status: $FRONTEND_STATUS"
fi

echo ""
echo "Step 3: Verify Backend API Endpoints"
echo "-------------------------------------"

# Check homework list endpoint (should require auth)
LIST_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8004/homework/list)
if [ "$LIST_STATUS" = "401" ]; then
    pass "Homework list endpoint requires authentication (401)"
else
    warn "List endpoint returned status: $LIST_STATUS (expected 401)"
fi

# Check upload endpoint (should require auth)
UPLOAD_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8004/homework/upload)
if [ "$UPLOAD_STATUS" = "401" ] || [ "$UPLOAD_STATUS" = "405" ]; then
    pass "Upload endpoint is protected (status: $UPLOAD_STATUS)"
else
    warn "Upload endpoint returned status: $UPLOAD_STATUS"
fi

echo ""
echo "Step 4: Verify Frontend Files"
echo "------------------------------"

# Check if HomeworkPanel component exists
if [ -f "../../frontend/src/components/homework-panel/HomeworkPanel.tsx" ]; then
    pass "HomeworkPanel.tsx exists"
else
    fail "HomeworkPanel.tsx not found"
fi

# Check if HomeworkUpload component exists
if [ -f "../../frontend/src/components/homework-panel/HomeworkUpload.tsx" ]; then
    pass "HomeworkUpload.tsx exists"
else
    fail "HomeworkUpload.tsx not found"
fi

# Check if HomeworkChat component exists
if [ -f "../../frontend/src/components/homework-panel/HomeworkChat.tsx" ]; then
    pass "HomeworkChat.tsx exists"
else
    fail "HomeworkChat.tsx not found"
fi

# Check if homework service exists
if [ -f "../../frontend/src/services/homework-service.ts" ]; then
    pass "homework-service.ts exists"
else
    fail "homework-service.ts not found"
fi

# Check if FloatingControlPanel imports HomeworkPanel
if grep -q "import.*HomeworkPanel" ../../frontend/src/components/floating-control-panel/FloatingControlPanel.tsx; then
    pass "FloatingControlPanel imports HomeworkPanel"
else
    fail "FloatingControlPanel does not import HomeworkPanel"
fi

# Check if FloatingControlPanel has homework state
if grep -q "homeworkOpen" ../../frontend/src/components/floating-control-panel/FloatingControlPanel.tsx; then
    pass "FloatingControlPanel has homeworkOpen state"
else
    fail "FloatingControlPanel missing homeworkOpen state"
fi

# Check if BookOpen icon is imported
if grep -q "BookOpen" ../../frontend/src/components/floating-control-panel/FloatingControlPanel.tsx; then
    pass "BookOpen icon is imported"
else
    fail "BookOpen icon not imported"
fi

echo ""
echo "Step 5: Verify Backend Files"
echo "-----------------------------"

# Check if api.py exists and has required endpoints
if [ -f "./api.py" ]; then
    pass "api.py exists"

    if grep -q "/homework/upload" ./api.py; then
        pass "Upload endpoint defined"
    else
        fail "Upload endpoint not found in api.py"
    fi

    if grep -q "/homework/list" ./api.py; then
        pass "List endpoint defined"
    else
        fail "List endpoint not found in api.py"
    fi

    if grep -q "/homework/assist" ./api.py; then
        pass "Assist endpoint defined"
    else
        fail "Assist endpoint not found in api.py"
    fi

    if grep -q "delete.*homework" ./api.py; then
        pass "Delete endpoint defined"
    else
        fail "Delete endpoint not found in api.py"
    fi
else
    fail "api.py not found"
fi

# Check if file_processor.py exists
if [ -f "./file_processor.py" ]; then
    pass "file_processor.py exists"
else
    fail "file_processor.py not found"
fi

# Check if homework_assistant.py exists
if [ -f "./homework_assistant.py" ]; then
    pass "homework_assistant.py exists"
else
    fail "homework_assistant.py not found"
fi

echo ""
echo "================================================"
echo "Summary"
echo "================================================"
echo -e "${GREEN}Passed:${NC} $PASSED"
echo -e "${YELLOW}Warnings:${NC} $WARNINGS"
echo -e "${RED}Failed:${NC} $FAILED"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All automated checks passed!${NC}"
    echo ""
    echo "Next step: Manual verification"
    echo "-------------------------------"
    echo "1. Open http://localhost:3000 in your browser"
    echo "2. Log in with valid credentials"
    echo "3. Follow the steps in E2E_VERIFICATION_CHECKLIST.md"
    echo ""
    exit 0
else
    echo -e "${RED}✗ Some checks failed. Please fix the issues above.${NC}"
    echo ""
    exit 1
fi
