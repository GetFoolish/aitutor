#!/usr/bin/env bash

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Clean up old logs and create a fresh logs directory
rm -rf "$SCRIPT_DIR/logs"
mkdir -p "$SCRIPT_DIR/logs"

# Detect and activate the Python virtual environment
if [[ -z "$VIRTUAL_ENV" ]]; then
    if [[ -d "$SCRIPT_DIR/venv" ]]; then
        echo "Activating local venv..."
        # shellcheck source=/dev/null
        source "$SCRIPT_DIR/venv/Scripts/activate" 2>/dev/null || source "$SCRIPT_DIR/venv/bin/activate"
    elif [[ -d "$SCRIPT_DIR/env" ]]; then
        echo "Activating local env..."
        # shellcheck source=/dev/null
        source "$SCRIPT_DIR/env/Scripts/activate" 2>/dev/null || source "$SCRIPT_DIR/env/bin/activate"
    elif [[ -d "$SCRIPT_DIR/.env" ]]; then
        echo "Activating local .env..."
        # shellcheck source=/dev/null
        source "$SCRIPT_DIR/.env/Scripts/activate" 2>/dev/null || source "$SCRIPT_DIR/.env/bin/activate"
    else
        echo "❌ No virtual environment found."
        echo "👉 Please create one with:"
        echo "    python -m venv venv"
        echo "    source venv/bin/activate"
        echo "👉 Next, install the required packages with:"
        echo "    pip install -r requirements.txt"
        echo "👉 Finally, run this script again."
        exit 1
    fi
else
    echo "Using already active virtual environment: $VIRTUAL_ENV"
fi

# ---------------------------------------------------------------------------
# Force Python to point explicitly to the venv interpreter (Windows-safe)
# ---------------------------------------------------------------------------

# Prefer Python from venv/env/Scripts (Windows) or venv/env/bin (Unix)
if [[ -x "$SCRIPT_DIR/venv/Scripts/python.exe" ]]; then
    PYTHON_BIN="$SCRIPT_DIR/venv/Scripts/python.exe"
elif [[ -x "$SCRIPT_DIR/venv/bin/python" ]]; then
    PYTHON_BIN="$SCRIPT_DIR/venv/bin/python"
elif [[ -x "$SCRIPT_DIR/env/Scripts/python.exe" ]]; then
    PYTHON_BIN="$SCRIPT_DIR/env/Scripts/python.exe"
elif [[ -x "$SCRIPT_DIR/.env/Scripts/python.exe" ]]; then
    PYTHON_BIN="$SCRIPT_DIR/.env/Scripts/python.exe"
elif [[ -x "$SCRIPT_DIR/env/bin/python" ]]; then
    PYTHON_BIN="$SCRIPT_DIR/env/bin/python"
elif [[ -x "$SCRIPT_DIR/.env/bin/python" ]]; then
    PYTHON_BIN="$SCRIPT_DIR/.env/bin/python"
else
    # fallback to whatever python is active
    PYTHON_BIN="$(command -v python3 || command -v python)"
fi

echo "Using Python: $PYTHON_BIN"

# Double-check Python source
echo "Python executable check -> $("$PYTHON_BIN" -c 'import sys; print(sys.executable)')"

# ---------------------------------------------------------------------------

# Array to hold the PIDs of background processes
pids=()

cleanup() {
    echo "Shutting down tutor..."
    for pid in "${pids[@]}"; do
        echo "Killing process $pid"
        kill "$pid" 2>/dev/null
    done
    echo "All processes terminated."
}
trap cleanup INT

# Start the Python backend in the background
echo "Starting Python backend... Logs -> logs/mediamixer.log"
(cd "$SCRIPT_DIR" && "$PYTHON_BIN" MediaMixer/media_mixer.py) > "$SCRIPT_DIR/logs/mediamixer.log" 2>&1 &
pids+=($!)

# Start the DASH API server in the background
echo "Starting DASH API server... Logs -> logs/api.log"
(cd "$SCRIPT_DIR" && "$PYTHON_BIN" DashSystem/dash_api.py) > "$SCRIPT_DIR/logs/api.log" 2>&1 &
pids+=($!)

# Start the SherlockED Exam API server in the background
echo "Starting SherlockED Exam API server... Logs -> logs/sherlocked_exam.log"
(cd "$SCRIPT_DIR/SherlockEDApi" && "$PYTHON_BIN" run_backend.py) > "$SCRIPT_DIR/logs/sherlocked_exam.log" 2>&1 &
pids+=($!)

# Give the backend servers a moment to start
echo "Waiting for backend services to initialize..."
sleep 2

# Start the Node.js frontend in the background
echo "Starting Node.js frontend... Logs -> logs/frontend.log"
(cd "$SCRIPT_DIR/frontend" && npm run dev) > "$SCRIPT_DIR/logs/frontend.log" 2>&1 &
pids+=($!)

echo "Tutor is running with the following PIDs: ${pids[*]}"
echo "Press Ctrl+C to stop."
echo "You can view the logs for each service in the 'logs' directory."

# Wait indefinitely until the script is interrupted
wait
