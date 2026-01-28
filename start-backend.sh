#!/bin/bash
# Start Homework Assistant Backend
# This script starts the backend server on port 8004

echo "🚀 Starting Homework Assistant Backend..."
echo ""

# Navigate to project root
cd "$(dirname "$0")"

# Activate virtual environment
source venv/bin/activate

# Load environment variables
export $(cat .env | grep -v '^#' | xargs)

# Start the backend server
echo "Backend will be available at: http://localhost:8004"
echo "API Documentation: http://localhost:8004/docs"
echo ""
echo "Press Ctrl+C to stop the server"
echo "========================================"
echo ""

cd services/HomeworkAssistant
python3 api.py
