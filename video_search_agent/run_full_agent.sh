#!/bin/bash

# Activate virtual environment
source ../venv/bin/activate

# Set API keys
export YOUTUBE_API_KEY="AIzaSyB3Qm7DI9swfzv6aF5sJeUy1mOUW0bm2I0"
export VIMEO_API_KEY="5ef882523f5d85a22d64e94c82bcb43f"
export ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY}"

# Run the main agent
echo "=========================================="
echo "Starting Video Search Agent"
echo "=========================================="
echo ""
echo "Processing all topics from: ../files (1)"
echo ""

python3 main_agent.py "../files (1)"

echo ""
echo "=========================================="
echo "Complete! Check output/ directory"
echo "=========================================="
