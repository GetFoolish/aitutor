#!/bin/bash
# Start all services with proper Node.js version

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

echo "🚀 Starting All Services"
echo "========================"
echo ""

# Load nvm if available
if [ -s "$HOME/.nvm/nvm.sh" ]; then
    echo "📦 Loading nvm..."
    source "$HOME/.nvm/nvm.sh"
    
    # Use Node 20 if available, otherwise 22
    if nvm list 20 2>/dev/null | grep -q "v20"; then
        echo "✅ Switching to Node.js 20"
        nvm use 20 >/dev/null 2>&1
    elif nvm list 22 2>/dev/null | grep -q "v22"; then
        echo "✅ Switching to Node.js 22"
        nvm use 22 >/dev/null 2>&1
    else
        echo "⚠️  Node.js 20/22 not found. Installing Node 20..."
        nvm install 20
        nvm use 20
    fi
    echo "   Using Node.js: $(node --version)"
    echo ""
fi

# Verify Node.js version
NODE_MAJOR=$(node --version 2>/dev/null | sed 's/v//' | cut -d. -f1)
if [ -z "$NODE_MAJOR" ] || [ "$NODE_MAJOR" -lt 20 ]; then
    echo "❌ Node.js version too old: $(node --version 2>/dev/null || echo 'unknown')"
    echo "   Required: Node.js 20.19+ or 22.12+"
    echo ""
    echo "   Quick fix:"
    echo "   source ~/.nvm/nvm.sh && nvm use 20"
    exit 1
fi

# Load environment variables
if [[ -f ".env" ]]; then
    echo "📝 Loading environment variables..."
    set -a
    source .env
    set +a
    echo "✅ Environment variables loaded"
    echo ""
fi

# Activate Python virtual environment
if [[ -z "$VIRTUAL_ENV" ]]; then
    if [[ -d "env" ]]; then
        echo "🐍 Activating Python virtual environment..."
        source env/bin/activate
    elif [[ -d "venv" ]]; then
        source venv/bin/activate
    fi
fi

# Start backend services using run_tutor.sh but don't start frontend
echo "🔧 Starting backend services..."
echo ""

# Start DASH API
echo "Starting DASH API..."
python services/DashSystem/dash_api.py > logs/dash_api.log 2>&1 &
DASH_PID=$!
echo "  DASH API PID: $DASH_PID"

# Start Auth Service
echo "Starting Auth Service..."
python services/AuthService/auth_api.py > logs/auth_service.log 2>&1 &
AUTH_PID=$!
echo "  Auth Service PID: $AUTH_PID"

# Start other services
echo "Starting SherlockED API..."
python services/SherlockEDApi/run_backend.py > logs/sherlocked_exam.log 2>&1 &
SHERLOCKED_PID=$!

echo "Starting TeachingAssistant API..."
python services/TeachingAssistant/api.py > logs/teaching_assistant.log 2>&1 &
TA_PID=$!

# Wait for backend services
echo ""
echo "⏳ Waiting for backend services to start..."
sleep 3

# Check DASH API
for i in {1..30}; do
    if curl -s http://localhost:8000/health >/dev/null 2>&1; then
        echo "✅ DASH API is ready"
        break
    fi
    sleep 1
done

# Start frontend
echo ""
echo "🌐 Starting frontend..."
cd frontend
npm run dev > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..

echo ""
echo "✅ All services started!"
echo ""
echo "📡 Service URLs:"
echo "  🌐 Frontend:           http://localhost:3000"
echo "  🔐 Auth Service:       http://localhost:8003"
echo "  🔧 DASH API:           http://localhost:8000"
echo "  🕵️  SherlockED API:     http://localhost:8001"
echo "  👨‍🏫 TeachingAssistant:  http://localhost:8002"
echo ""
echo "📋 Process IDs:"
echo "  DASH API: $DASH_PID"
echo "  Auth Service: $AUTH_PID"
echo "  Frontend: $FRONTEND_PID"
echo ""
echo "📝 Logs:"
echo "  Backend: logs/dash_api.log, logs/auth_service.log"
echo "  Frontend: logs/frontend.log"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Wait for user interrupt
trap "echo ''; echo 'Stopping services...'; kill $DASH_PID $AUTH_PID $SHERLOCKED_PID $TA_PID $FRONTEND_PID 2>/dev/null; exit" INT

wait

