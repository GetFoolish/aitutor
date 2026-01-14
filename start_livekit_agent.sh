#!/bin/bash
# Start LiveKit Agent for testing

cd "$(dirname "$0")"
source env/bin/activate 2>/dev/null || source venv/bin/activate 2>/dev/null || echo "No venv found, using system Python"

cd services/LiveKitAgent
python agent.py dev > ../../logs/livekit_agent.log 2>&1 &
echo "LiveKit Agent started (PID: $!)"
echo "Logs: logs/livekit_agent.log"
