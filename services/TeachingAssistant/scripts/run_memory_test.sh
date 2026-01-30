#!/bin/bash
# Memory System Test Pipeline
#
# This script runs the full test pipeline:
# 1. Generate simulated conversations from a persona
# 2. Process sessions through the memory system
# 3. Generate the Living Biography
#
# Usage:
#   ./run_memory_test.sh [sessions] [turns_per_session]
#
# Example:
#   ./run_memory_test.sh 20 25

SESSIONS=${1:-20}
TURNS=${2:-25}
PERSONA="leo_takahashi.json"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=============================================="
echo "Memory System Test Pipeline"
echo "=============================================="
echo "Persona: $PERSONA"
echo "Sessions: $SESSIONS"
echo "Turns per session: $TURNS"
echo "=============================================="

# Step 1: Generate conversations
echo ""
echo "[STEP 1] Generating simulated conversations..."
echo "=============================================="
python generate_conversation.py \
    --persona "$PERSONA" \
    --sessions "$SESSIONS" \
    --turns-per-session "$TURNS" \
    --output simulated_sessions

if [ $? -ne 0 ]; then
    echo "ERROR: Conversation generation failed"
    exit 1
fi

# Step 2: Process through memory system
echo ""
echo "[STEP 2] Processing through memory system..."
echo "=============================================="
python process_sessions.py \
    --sessions-dir simulated_sessions/leo_takahashi

if [ $? -ne 0 ]; then
    echo "ERROR: Memory processing failed"
    exit 1
fi

# Step 3: Display results
echo ""
echo "[STEP 3] Results Summary"
echo "=============================================="
echo ""
echo "Generated Files:"
ls -la simulated_sessions/leo_takahashi/
echo ""
echo "Memory Results:"
ls -la simulated_sessions/leo_takahashi/memory_results/
echo ""
echo "Living Biography:"
echo "=============================================="
cat simulated_sessions/leo_takahashi/memory_results/living_biography.txt
echo ""
echo "=============================================="
echo "Test Complete!"
echo "=============================================="
