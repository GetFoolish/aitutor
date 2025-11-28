# PowerShell script to run the AI Tutor system on Windows
# Equivalent to run_tutor.sh for Mac/Linux

# Get the directory where the script is located
$SCRIPT_DIR = $PSScriptRoot

# Clean up old logs and create a fresh logs directory
if (Test-Path "$SCRIPT_DIR\logs") {
    Remove-Item -Path "$SCRIPT_DIR\logs" -Recurse -Force
}
New-Item -ItemType Directory -Path "$SCRIPT_DIR\logs" -Force | Out-Null

# Detect Python environment
$PYTHON_BIN = $null
$VENV_ACTIVATED = $false

if (-not $env:VIRTUAL_ENV) {
    # Not already in a virtual environment
    if (Test-Path "$SCRIPT_DIR\env\Scripts\Activate.ps1") {
        Write-Host "Activating local env..."
        & "$SCRIPT_DIR\env\Scripts\Activate.ps1"
        $VENV_ACTIVATED = $true
    }
    elseif (Test-Path "$SCRIPT_DIR\.env\Scripts\Activate.ps1") {
        Write-Host "Activating local .env..."
        & "$SCRIPT_DIR\.env\Scripts\Activate.ps1"
        $VENV_ACTIVATED = $true
    }
    else {
        Write-Host "No virtual environment found."
        Write-Host "Please create one with:"
        Write-Host "    python -m venv env"
        Write-Host "    .\env\Scripts\Activate.ps1"
        Write-Host "Next, install the required packages with:"
        Write-Host "    pip install -r requirements.txt"
        Write-Host "If you plan to use the frontend, also run:"
        Write-Host "    cd frontend"
        Write-Host "    npm install --force"
        Write-Host "    cd .."
        Write-Host "Finally, run this script again."
        exit 1
    }
}
else {
    Write-Host "Using already active virtual environment: $env:VIRTUAL_ENV"
}

# Get the python executable (now guaranteed to be from venv)
if ($env:VIRTUAL_ENV) {
    # Use the venv's Python explicitly
    if (Test-Path "$env:VIRTUAL_ENV\Scripts\python.exe") {
        # Windows native path
        $PYTHON_BIN = "$env:VIRTUAL_ENV\Scripts\python.exe"
    }
    elseif (Test-Path "$env:VIRTUAL_ENV\bin\python3") {
        # Unix-style path (Git Bash/WSL)
        $PYTHON_BIN = "$env:VIRTUAL_ENV\bin\python3"
    }
    elseif (Test-Path "$env:VIRTUAL_ENV\bin\python") {
        $PYTHON_BIN = "$env:VIRTUAL_ENV\bin\python"
    }
    else {
        # Fallback to PATH search if venv Python not found
        $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
        if (-not $pythonCmd) {
            $pythonCmd = Get-Command python3 -ErrorAction SilentlyContinue
        }
        if ($pythonCmd) {
            $PYTHON_BIN = $pythonCmd.Source
        }
        Write-Host "Warning: Could not find venv Python, using: $PYTHON_BIN"
    }
}
else {
    # No venv active, search PATH
    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if (-not $pythonCmd) {
        $pythonCmd = Get-Command python3 -ErrorAction SilentlyContinue
    }
    if ($pythonCmd) {
        $PYTHON_BIN = $pythonCmd.Source
    }
    else {
        Write-Host "Python not found in PATH"
        exit 1
    }
}

Write-Host "Using Python: $PYTHON_BIN"

# Array to hold the process objects
$processes = @()

# Function to clean up background processes
function Cleanup {
    Write-Host ""
    Write-Host "Shutting down tutor..."
    foreach ($proc in $processes) {
        if ($proc -and -not $proc.HasExited) {
            Write-Host "Killing process $($proc.Id)"
            Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
        }
    }
    Write-Host "All processes terminated."
}

# Function to handle Ctrl+C
$null = Register-EngineEvent PowerShell.Exiting -Action { Cleanup }

# Also handle Ctrl+C directly
$Host.UI.RawUI.WindowTitle = "AI Tutor - Press Ctrl+C to stop"

# Start the Python backend in the background
Write-Host "Starting Python backend... Logs -> logs/mediamixer.log"
$proc = Start-Process -FilePath "cmd" -ArgumentList "/c", "`"$PYTHON_BIN`" services\MediaMixer\media_mixer.py 2>&1" -WorkingDirectory $SCRIPT_DIR -NoNewWindow -PassThru -RedirectStandardOutput "$SCRIPT_DIR\logs\mediamixer.log"
$processes += $proc

# Start the FastAPI server in the background
Write-Host "Starting DASH API server... Logs -> logs/dash_api.log"
$proc = Start-Process -FilePath "cmd" -ArgumentList "/c", "`"$PYTHON_BIN`" services\DashSystem\dash_api.py 2>&1" -WorkingDirectory $SCRIPT_DIR -NoNewWindow -PassThru -RedirectStandardOutput "$SCRIPT_DIR\logs\dash_api.log"
$processes += $proc

# Start the SherlockEDExam FastAPI server in the background
Write-Host "Starting SherlockED Exam API server... Logs -> logs/sherlocked_exam.log"
$proc = Start-Process -FilePath "cmd" -ArgumentList "/c", "`"$PYTHON_BIN`" services\SherlockEDApi\run_backend.py 2>&1" -WorkingDirectory $SCRIPT_DIR -NoNewWindow -PassThru -RedirectStandardOutput "$SCRIPT_DIR\logs\sherlocked_exam.log"
$processes += $proc

# Start the Tutor service (Node.js backend for Gemini Live API)
Write-Host "Starting Tutor service (Adam)... Logs -> logs/tutor.log"
$proc = Start-Process -FilePath "cmd" -ArgumentList "/c", "node server.js 2>&1" -WorkingDirectory "$SCRIPT_DIR\services\Tutor" -NoNewWindow -PassThru -RedirectStandardOutput "$SCRIPT_DIR\logs\tutor.log"
$processes += $proc

# Start the TeachingAssistant API server in the background
Write-Host "Starting TeachingAssistant API server... Logs -> logs/teaching_assistant.log"
$proc = Start-Process -FilePath "cmd" -ArgumentList "/c", "`"$PYTHON_BIN`" services\TeachingAssistant\api.py 2>&1" -WorkingDirectory $SCRIPT_DIR -NoNewWindow -PassThru -RedirectStandardOutput "$SCRIPT_DIR\logs\teaching_assistant.log"
$processes += $proc

# Start the Memory Watcher for real-time memory extraction
Write-Host "Starting Memory Watcher... Logs -> logs/memory_watcher.log"
$proc = Start-Process -FilePath "cmd" -ArgumentList "/c", "chcp 65001 >nul && `"$PYTHON_BIN`" -m Memory.consolidator 2>&1" -WorkingDirectory $SCRIPT_DIR -NoNewWindow -PassThru -RedirectStandardOutput "$SCRIPT_DIR\logs\memory_watcher.log"
$processes += $proc

# Give the backend servers a moment to start
Write-Host "Waiting for backend services to initialize..."
Start-Sleep -Seconds 3

# Extract ports dynamically from configuration files
$FRONTEND_PORT = "3000"
$DASH_API_PORT = "8000"
$SHERLOCKED_API_PORT = "8001"
$TEACHING_ASSISTANT_PORT = "8002"
$MEDIAMIXER_PORT = "8765"

# Extract frontend port from vite.config.ts
if (Test-Path "$SCRIPT_DIR\frontend\vite.config.ts") {
    $content = Get-Content "$SCRIPT_DIR\frontend\vite.config.ts" -Raw
    if ($content -match '"port"\s*:\s*(\d+)') {
        $FRONTEND_PORT = $matches[1]
    }
}

# Extract DASH API port
if (Test-Path "$SCRIPT_DIR\services\DashSystem\dash_api.py") {
    $content = Get-Content "$SCRIPT_DIR\services\DashSystem\dash_api.py" -Raw
    if ($content -match 'port\s*=\s*(\d+)') {
        $DASH_API_PORT = $matches[1]
    }
}

# Extract SherlockED API port
if (Test-Path "$SCRIPT_DIR\services\SherlockEDApi\run_backend.py") {
    $content = Get-Content "$SCRIPT_DIR\services\SherlockEDApi\run_backend.py" -Raw
    if ($content -match 'port\s*=\s*(\d+)') {
        $SHERLOCKED_API_PORT = $matches[1]
    }
}

# Extract TeachingAssistant port
if (Test-Path "$SCRIPT_DIR\services\TeachingAssistant\api.py") {
    $content = Get-Content "$SCRIPT_DIR\services\TeachingAssistant\api.py" -Raw
    if ($content -match 'port\s*=\s*(\d+)') {
        $TEACHING_ASSISTANT_PORT = $matches[1]
    }
}

# Extract MediaMixer port
if (Test-Path "$SCRIPT_DIR\services\MediaMixer\media_mixer.py") {
    $content = Get-Content "$SCRIPT_DIR\services\MediaMixer\media_mixer.py" -Raw
    if ($content -match "PORT'\s*,\s*(\d+)") {
        $MEDIAMIXER_PORT = $matches[1]
    }
}

$MEDIAMIXER_COMMAND_PORT = $MEDIAMIXER_PORT
$MEDIAMIXER_VIDEO_PORT = $MEDIAMIXER_PORT

# Start the Node.js frontend in the background
Write-Host "Starting Node.js frontend... Logs -> logs/frontend.log"
$proc = Start-Process -FilePath "cmd" -ArgumentList "/c", "npm run dev 2>&1" -WorkingDirectory "$SCRIPT_DIR\frontend" -NoNewWindow -PassThru -RedirectStandardOutput "$SCRIPT_DIR\logs\frontend.log"
$processes += $proc

$pids = $processes | ForEach-Object { $_.Id }
Write-Host "Tutor is running with the following PIDs: $($pids -join ', ')"
Write-Host ""
Write-Host "Service URLs:"
Write-Host "  Frontend:           http://localhost:$FRONTEND_PORT"
Write-Host "  DASH API:           http://localhost:$DASH_API_PORT"
Write-Host "  SherlockED API:     http://localhost:$SHERLOCKED_API_PORT"
Write-Host "  TeachingAssistant:  http://localhost:$TEACHING_ASSISTANT_PORT"
Write-Host "  Tutor Service:      ws://localhost:8767"
Write-Host "  Memory Watcher:     Running (logs/memory_watcher.log)"
Write-Host "  MediaMixer Command: ws://localhost:$MEDIAMIXER_COMMAND_PORT/command"
Write-Host "  MediaMixer Video:   ws://localhost:$MEDIAMIXER_VIDEO_PORT/video"
Write-Host ""
Write-Host "Press Ctrl+C to stop."
Write-Host "You can view the logs for each service in the logs directory."

# Wait indefinitely until the script is interrupted
try {
    while ($true) {
        Start-Sleep -Seconds 1
        # Check if any process has exited unexpectedly
        $exited = $processes | Where-Object { $_.HasExited }
        if ($exited) {
            Write-Host "Warning: Some processes have exited unexpectedly"
            foreach ($proc in $exited) {
                $procId = $proc.Id
                Write-Host ('  Process ' + $procId + ' has exited')
            }
        }
    }
}
finally {
    # Handle Ctrl+C or script termination
    Cleanup
}
