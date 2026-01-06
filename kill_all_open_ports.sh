#!/usr/bin/env bash

# Script to kill all processes on tutor service ports
# Ports: 3000 (Frontend), 8000 (DASH API), 8001 (SherlockED), 8002 (TeachingAssistant), 8003 (Auth)

echo "🔍 Looking for processes on tutor service ports..."

PORTS=(3000 8000 8001 8002 8003)

for PORT in "${PORTS[@]}"; do
    echo ""
    echo "Checking port $PORT..."

    # Find PIDs using lsof
    PIDS=$(lsof -ti:$PORT 2>/dev/null)

    if [ -z "$PIDS" ]; then
        echo "  ✅ Port $PORT is free"
    else
        echo "  ❌ Port $PORT is in use by PID(s): $PIDS"
        echo "  🔪 Killing process(es)..."

        # Kill each PID
        for PID in $PIDS; do
            kill -9 $PID 2>/dev/null
            if [ $? -eq 0 ]; then
                echo "     ✓ Killed PID $PID"
            else
                echo "     ✗ Failed to kill PID $PID (might require sudo)"
            fi
        done
    fi
done

echo ""
echo "✅ All tutor service ports have been cleared!"
