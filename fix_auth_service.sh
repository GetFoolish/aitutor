#!/bin/bash
# Fix auth service - restart with proper environment

cd "$(dirname "$0")"

echo "🔧 Fixing Auth Service"
echo "======================"
echo ""

# Kill existing auth service
echo "Stopping existing auth service..."
pkill -f "auth_api.py"
sleep 2

# Load environment
if [[ -f ".env" ]]; then
    set -a
    source .env
    set +a
fi

# Ensure BYPASS_AUTH is set
export BYPASS_AUTH=true
export GEMINI_API_KEY=${GEMINI_API_KEY:-$(grep GEMINI_API_KEY .env 2>/dev/null | cut -d= -f2)}

echo "✅ Environment loaded"
echo "   BYPASS_AUTH=$BYPASS_AUTH"
echo "   GEMINI_API_KEY=${GEMINI_API_KEY:0:20}..."
echo ""

# Activate Python environment
if [[ -z "$VIRTUAL_ENV" ]]; then
    if [[ -d "env" ]]; then
        source env/bin/activate
    elif [[ -d "venv" ]]; then
        source venv/bin/activate
    fi
fi

# Start auth service
echo "Starting Auth Service..."
python services/AuthService/auth_api.py > logs/auth_service.log 2>&1 &
AUTH_PID=$!
echo "  Auth Service PID: $AUTH_PID"
echo ""

# Wait for service to start
echo "Waiting for service to start..."
sleep 3

# Test the endpoint
echo "Testing /auth/gemini-token endpoint..."
RESPONSE=$(curl -s http://localhost:8003/auth/gemini-token 2>&1)

if echo "$RESPONSE" | grep -q "token"; then
    echo "✅ SUCCESS! Endpoint is working"
    echo "   Response: $(echo $RESPONSE | head -c 100)..."
elif echo "$RESPONSE" | grep -q "404"; then
    echo "❌ Still getting 404"
    echo "   Checking logs..."
    tail -20 logs/auth_service.log
elif echo "$RESPONSE" | grep -q "500"; then
    echo "⚠️  Getting 500 error (might be missing GEMINI_API_KEY)"
    echo "   Response: $RESPONSE"
else
    echo "⚠️  Unexpected response: $RESPONSE"
fi

echo ""
echo "📝 Logs: tail -f logs/auth_service.log"
echo "🧪 Test: curl http://localhost:8003/auth/gemini-token"

