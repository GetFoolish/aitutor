#!/bin/bash
# Restart services with BYPASS_AUTH enabled

cd "$(dirname "$0")"

echo "🔄 Restarting Services with Auth Bypass"
echo "========================================"
echo ""

# Kill existing services
echo "Stopping existing services..."
pkill -f "dash_api.py" 2>/dev/null
pkill -f "auth_api.py" 2>/dev/null
pkill -f "run_backend.py" 2>/dev/null
pkill -f "api.py" 2>/dev/null
sleep 2

# Note: Authentication is enabled (BYPASS_AUTH removed)
echo "✅ Authentication enabled - login required"
echo ""

# Activate Python virtual environment
if [[ -z "$VIRTUAL_ENV" ]]; then
    if [[ -d "env" ]]; then
        source env/bin/activate
    elif [[ -d "venv" ]]; then
        source venv/bin/activate
    fi
fi

# Load environment variables
if [[ -f ".env" ]]; then
    set -a
    source .env
    set +a
    # Fix API keys that might have newlines
    export GEMINI_API_KEY=$(echo "$GEMINI_API_KEY" | tr -d '\n\r')
    export GOOGLE_API_KEY=$(echo "$GOOGLE_API_KEY" | tr -d '\n\r')
fi

# Start services
echo "Starting DASH API..."
python services/DashSystem/dash_api.py > logs/dash_api.log 2>&1 &
DASH_PID=$!
echo "  DASH API PID: $DASH_PID"

echo "Starting Auth Service..."
python services/AuthService/auth_api.py > logs/auth_service.log 2>&1 &
AUTH_PID=$!
echo "  Auth Service PID: $AUTH_PID"

echo "Starting SherlockED API..."
python services/SherlockEDApi/run_backend.py > logs/sherlocked_exam.log 2>&1 &
SHERLOCKED_PID=$!

echo "Starting TeachingAssistant API..."
python services/TeachingAssistant/api.py > logs/teaching_assistant.log 2>&1 &
TA_PID=$!

echo ""
echo "⏳ Waiting for services to start..."
sleep 5

# Check services
echo ""
echo "Checking service status..."

# Check Auth Service
if curl -s http://localhost:8003/health >/dev/null 2>&1; then
    echo "✅ Auth Service (8003): Running"
else
    echo "❌ Auth Service (8003): Not responding"
fi

# Check DASH API (may still be initializing)
if curl -s http://localhost:8000/health 2>/dev/null | grep -q "ready"; then
    echo "✅ DASH API (8000): Ready"
elif curl -s http://localhost:8000/health >/dev/null 2>&1; then
    echo "⏳ DASH API (8000): Initializing (this can take 30-60 seconds)"
else
    echo "❌ DASH API (8000): Not responding"
fi

echo ""
echo "📝 Logs:"
echo "  DASH API: tail -f logs/dash_api.log"
echo "  Auth Service: tail -f logs/auth_service.log"
echo ""
echo "🧪 Test Auth Bypass:"
echo "  curl http://localhost:8003/auth/gemini-token"
echo ""
echo "Press Ctrl+C to stop all services"

# Wait for interrupt
trap "echo ''; echo 'Stopping services...'; kill $DASH_PID $AUTH_PID $SHERLOCKED_PID $TA_PID 2>/dev/null; exit" INT
wait

