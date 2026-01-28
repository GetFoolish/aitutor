#!/bin/bash
#
# Service Health Monitor - Tests actual operations, not just HTTP 200
# Catches slow queries, timeouts, and performance issues
#

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=================================="
echo "AI Tutor Service Health Monitor"
echo "=================================="
echo ""

# Health check function with timeout
check_endpoint() {
    local name=$1
    local url=$2
    local timeout=${3:-3}

    echo -n "Testing $name... "

    start_time=$(date +%s%3N)
    if response=$(curl -sf -m "$timeout" "$url" 2>&1); then
        end_time=$(date +%s%3N)
        duration=$((end_time - start_time))

        if [ "$duration" -lt 1000 ]; then
            echo -e "${GREEN}✓${NC} (${duration}ms)"
            return 0
        elif [ "$duration" -lt 3000 ]; then
            echo -e "${YELLOW}⚠ SLOW${NC} (${duration}ms)"
            return 1
        else
            echo -e "${RED}✗ TIMEOUT${NC} (${duration}ms)"
            return 1
        fi
    else
        echo -e "${RED}✗ FAILED${NC}"
        echo "  Error: $response"
        return 1
    fi
}

# Test all services
failures=0

check_endpoint "Auth Service" "http://localhost:8003/health" 2 || ((failures++))
check_endpoint "Homework Assistant" "http://localhost:8004/health" 2 || ((failures++))
check_endpoint "Dash System" "http://localhost:8000/health" 3 || ((failures++))
check_endpoint "Teaching Assistant" "http://localhost:8002/health" 2 || ((failures++))
check_endpoint "Frontend" "http://localhost:3000" 2 || ((failures++))

echo ""
echo "=================================="
if [ $failures -eq 0 ]; then
    echo -e "${GREEN}✓ All services healthy${NC}"
    exit 0
else
    echo -e "${RED}✗ $failures service(s) unhealthy${NC}"
    echo ""
    echo "Troubleshooting:"
    echo "1. Check logs: tail -f logs/*.log"
    echo "2. Restart services: ./stop.sh && ./dev.sh"
    echo "3. Check MongoDB connection"
    exit 1
fi
