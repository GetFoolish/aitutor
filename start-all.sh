#!/bin/bash
# Start both Frontend and Backend for AITutor
# This script starts both services in separate terminal windows/tabs

echo "🚀 Starting AITutor - Full Stack"
echo "========================================"
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Check if we're on macOS
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "📱 Opening Backend in new Terminal tab..."
    osascript -e "tell application \"Terminal\"
        do script \"cd '$SCRIPT_DIR' && ./start-backend.sh\"
    end tell"

    sleep 2

    echo "🎨 Opening Frontend in new Terminal tab..."
    osascript -e "tell application \"Terminal\"
        do script \"cd '$SCRIPT_DIR' && ./start-frontend.sh\"
    end tell"

    echo ""
    echo "✅ Services starting in separate Terminal tabs!"
    echo ""
    echo "Backend: http://localhost:8004"
    echo "Frontend: http://localhost:5173"
    echo "API Docs: http://localhost:8004/docs"
    echo ""
    echo "Close the terminal tabs to stop the servers."
else
    # For Linux/Windows, start in background
    echo "🔧 Starting Backend..."
    cd "$SCRIPT_DIR"
    ./start-backend.sh > /tmp/backend.log 2>&1 &
    BACKEND_PID=$!
    echo "Backend PID: $BACKEND_PID"

    sleep 3

    echo "🎨 Starting Frontend..."
    ./start-frontend.sh > /tmp/frontend.log 2>&1 &
    FRONTEND_PID=$!
    echo "Frontend PID: $FRONTEND_PID"

    echo ""
    echo "✅ Services started in background!"
    echo ""
    echo "Backend: http://localhost:8004 (PID: $BACKEND_PID)"
    echo "Frontend: http://localhost:5173 (PID: $FRONTEND_PID)"
    echo "API Docs: http://localhost:8004/docs"
    echo ""
    echo "Logs:"
    echo "  Backend: tail -f /tmp/backend.log"
    echo "  Frontend: tail -f /tmp/frontend.log"
    echo ""
    echo "To stop:"
    echo "  kill $BACKEND_PID $FRONTEND_PID"
fi
