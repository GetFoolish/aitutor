#!/usr/bin/env bash

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Clean up old logs and create a fresh logs directory
rm -rf "$SCRIPT_DIR/logs"
mkdir -p "$SCRIPT_DIR/logs"

# Detect Python environment
if [[ -z "$VIRTUAL_ENV" ]]; then
    # Not already in a virtual environment
    if [[ -d "$SCRIPT_DIR/env" ]]; then
        echo "Activating local env..."
        # shellcheck source=/dev/null
        source "$SCRIPT_DIR/env/bin/activate"
    elif [[ -d "$SCRIPT_DIR/.env" ]]; then
        echo "Activating local .env..."
        # shellcheck source=/dev/null
        source "$SCRIPT_DIR/.env/bin/activate"
    else
        echo "❌ No virtual environment found."
        echo "👉 Please create one with:"
        echo "    python -m venv env"
        echo "    source env/bin/activate"
        echo "👉 Next, install the required packages with:"
        echo "    pip install -r requirements.txt"
        echo "👉 If you plan to use the frontend, also run:"
        echo "    cd frontend"
        echo "    npm install --force"
        echo "    cd .."
        echo "👉 Finally, run this script again."
        exit 1
    fi
else
    echo "Using already active virtual environment: $VIRTUAL_ENV"
fi

# Get the python executable (now guaranteed to be from venv)
PYTHON_BIN="$(command -v python3 || command -v python)"
echo "Using Python: $PYTHON_BIN"

# Array to hold the PIDs of background processes
pids=()

# Function to clean up background processes
cleanup() {
    echo "Shutting down tutor..."
    for pid in "${pids[@]}"; do
        echo "Killing process $pid"
        kill "$pid"
    done
    echo "All processes terminated."
}

# Trap the INT signal (sent by Ctrl+C) to run the cleanup function
trap cleanup INT

# Start the Python backend in the background
echo "Starting Python backend... Logs -> logs/mediamixer.log"
(cd "$SCRIPT_DIR" && "$PYTHON_BIN" MediaMixer/media_mixer.py) > "$SCRIPT_DIR/logs/mediamixer.log" 2>&1 &
pids+=($!)

# Start the FastAPI server in the background
echo "Starting DASH API server... Logs -> logs/api.log"
(cd "$SCRIPT_DIR" && "$PYTHON_BIN" DashSystem/dash_api.py) > "$SCRIPT_DIR/logs/api.log" 2>&1 &
pids+=($!)

# Start the SherlockEDExam FastAPI server in the background
echo "Starting SherlockED Exam API server... Logs -> logs/sherlocked_exam.log"
(cd "$SCRIPT_DIR" && "$PYTHON_BIN" SherlockEDApi/run_backend.py) > "$SCRIPT_DIR/logs/sherlocked_exam.log" 2>&1 &
pids+=($!)

# Start the TeachingAssistant API server in the background
echo "Starting TeachingAssistant API server... Logs -> logs/teaching_assistant.log"
(cd "$SCRIPT_DIR" && "$PYTHON_BIN" TeachingAssistant/api.py) > "$SCRIPT_DIR/logs/teaching_assistant.log" 2>&1 &
pids+=($!)

# Give the backend servers a moment to start
echo "Waiting for backend services to initialize..."
sleep 2

# Extract ports dynamically from configuration files
FRONTEND_PORT=$(grep -o '"port":[[:space:]]*[0-9]*' "$SCRIPT_DIR/frontend/vite.config.ts" 2>/dev/null | grep -o '[0-9]*' || echo "3000")
DASH_API_PORT=$(grep -o 'port=[0-9]*' "$SCRIPT_DIR/DashSystem/dash_api.py" 2>/dev/null | grep -o '[0-9]*' || echo "8000")
SHERLOCKED_API_PORT=$(grep -o 'port=[0-9]*' "$SCRIPT_DIR/SherlockEDApi/run_backend.py" 2>/dev/null | grep -o '[0-9]*' || echo "8001")
TEACHING_ASSISTANT_PORT=$(grep -o 'port.*[0-9]*' "$SCRIPT_DIR/TeachingAssistant/api.py" 2>/dev/null | grep -o '[0-9]*' || echo "8002")
MEDIAMIXER_COMMAND_PORT=$(grep -o 'localhost",[[:space:]]*[0-9]*' "$SCRIPT_DIR/MediaMixer/media_mixer.py" 2>/dev/null | head -1 | grep -o '[0-9]*' || echo "8765")
MEDIAMIXER_VIDEO_PORT=$(grep -o 'localhost",[[:space:]]*[0-9]*' "$SCRIPT_DIR/MediaMixer/media_mixer.py" 2>/dev/null | tail -1 | grep -o '[0-9]*' || echo "8766")

# Start the Node.js frontend in the background
echo "Starting Node.js frontend... Logs -> logs/frontend.log"
(cd "$SCRIPT_DIR/frontend" && npm run dev) > "$SCRIPT_DIR/logs/frontend.log" 2>&1 &
pids+=($!)

echo "Tutor is running with the following PIDs: ${pids[*]}"
echo ""
echo "📡 Service URLs:"
echo "  🌐 Frontend:           http://localhost:$FRONTEND_PORT"
echo "  🔧 DASH API:           http://localhost:$DASH_API_PORT"
echo "  🕵️  SherlockED API:     http://localhost:$SHERLOCKED_API_PORT"
echo "  👨‍🏫 TeachingAssistant:  http://localhost:$TEACHING_ASSISTANT_PORT"
echo "  📹 MediaMixer Command: ws://localhost:$MEDIAMIXER_COMMAND_PORT"
echo "  📺 MediaMixer Video:   ws://localhost:$MEDIAMIXER_VIDEO_PORT"
echo ""
echo "Press Ctrl+C to stop."
echo "You can view the logs for each service in the 'logs' directory."

# Wait indefinitely until the script is interrupted
wait
