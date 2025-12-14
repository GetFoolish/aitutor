# PowerShell script to run the AI Tutor system on Windows
# Equivalent to run_tutor.sh for Mac/Linux

# Get the directory where the script is located
$SCRIPT_DIR = $PSScriptRoot

# Function to kill processes using specific ports
function Kill-ProcessOnPort {
    param([int]$Port)
    $connections = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
    foreach ($conn in $connections) {
        $processId = $conn.OwningProcess
        if ($processId) {
            Write-Host "Killing process $processId using port $Port"
            Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
            Start-Sleep -Milliseconds 500
        }
    }
}

# Load environment variables from .env file if it exists
if (Test-Path "$SCRIPT_DIR\.env") {
    Write-Host "Loading environment variables from .env file..."
    Get-Content "$SCRIPT_DIR\.env" | ForEach-Object {
        if ($_ -match '^\s*#') { return }  # Skip comments
        if ($_ -match '^\s*$') { return }  # Skip empty lines
        if ($_ -match '^\s*([^=]+)=(.*)$') {
            $key = $matches[1].Trim()
            $value = $matches[2].Trim()
            # Remove quotes from value if present
            $value = $value -replace '^["'']|["'']$', ''
            [Environment]::SetEnvironmentVariable($key, $value, "Process")
            Write-Host "  Loaded: $key"
        }
    }
    Write-Host "[OK] Environment variables loaded from .env"
} else {
    Write-Host "[WARNING] No .env file found. Using default values."
    Write-Host "   Create a .env file with your MongoDB Atlas URI and other config."
}

# Kill any existing processes using our ports
Write-Host "Checking for existing processes on ports..."
Kill-ProcessOnPort -Port 8767  # Tutor service
Kill-ProcessOnPort -Port 8000  # DASH API
Kill-ProcessOnPort -Port 8001  # SherlockED API
Kill-ProcessOnPort -Port 8002  # TeachingAssistant API
Kill-ProcessOnPort -Port 8003  # Auth Service
Kill-ProcessOnPort -Port 3000  # Frontend

# Wait a moment for processes to fully terminate
Start-Sleep -Seconds 2

# Clean up old logs - try to delete, but don't fail if locked
if (Test-Path "$SCRIPT_DIR\logs") {
    try {
        # Try to delete individual log files first
        Get-ChildItem -Path "$SCRIPT_DIR\logs" -File | ForEach-Object {
            try {
                Remove-Item $_.FullName -Force -ErrorAction Stop
            } catch {
                Write-Host "Warning: Could not delete $($_.Name) - it may be locked. Will truncate instead."
                # Truncate the file instead
                "" | Out-File $_.FullName -Force -ErrorAction SilentlyContinue
            }
        }
        # Try to remove empty directories
        Get-ChildItem -Path "$SCRIPT_DIR\logs" -Directory | ForEach-Object {
            try {
                Remove-Item $_.FullName -Recurse -Force -ErrorAction Stop
            } catch {
                Write-Host "Warning: Could not delete directory $($_.Name)"
            }
        }
    } catch {
        Write-Host "Warning: Could not fully clean logs directory. Continuing anyway..."
    }
}

# Ensure logs directory exists
if (-not (Test-Path "$SCRIPT_DIR\logs")) {
    New-Item -ItemType Directory -Path "$SCRIPT_DIR\logs" -Force | Out-Null
}

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
# Check if port 8767 is still in use
$port8767 = Get-NetTCPConnection -LocalPort 8767 -ErrorAction SilentlyContinue
if ($port8767) {
    Write-Host "Warning: Port 8767 is still in use. Attempting to kill process..."
    Kill-ProcessOnPort -Port 8767
    Start-Sleep -Seconds 1
}
$proc = Start-Process -FilePath "cmd" -ArgumentList "/c", "node server.js 2>&1" -WorkingDirectory "$SCRIPT_DIR\services\Tutor" -NoNewWindow -PassThru -RedirectStandardOutput "$SCRIPT_DIR\logs\tutor.log"
$processes += $proc

# Start the TeachingAssistant API server in the background
Write-Host "Starting TeachingAssistant API server... Logs -> logs/teaching_assistant.log"
$proc = Start-Process -FilePath "cmd" -ArgumentList "/c", "`"$PYTHON_BIN`" services\TeachingAssistant\api.py 2>&1" -WorkingDirectory $SCRIPT_DIR -NoNewWindow -PassThru -RedirectStandardOutput "$SCRIPT_DIR\logs\teaching_assistant.log"
$processes += $proc

# Start the Auth Service API server in the background
Write-Host "Starting Auth Service API server... Logs -> logs/auth_service.log"
$proc = Start-Process -FilePath "cmd" -ArgumentList "/c", "`"$PYTHON_BIN`" services\AuthService\auth_api.py 2>&1" -WorkingDirectory $SCRIPT_DIR -NoNewWindow -PassThru -RedirectStandardOutput "$SCRIPT_DIR\logs\auth_service.log"
$processes += $proc

# Give the backend servers a moment to start
Write-Host "Waiting for backend services to initialize..."
Start-Sleep -Seconds 3

# Extract ports dynamically from configuration files
$FRONTEND_PORT = "3000"
$DASH_API_PORT = "8000"
$SHERLOCKED_API_PORT = "8001"
$TEACHING_ASSISTANT_PORT = "8002"
$AUTH_SERVICE_PORT = "8003"

# Extract frontend port from vite.config.ts
if (Test-Path "$SCRIPT_DIR\frontend\vite.config.ts") {
    $content = Get-Content "$SCRIPT_DIR\frontend\vite.config.ts" -Raw
    if ($content -match '"port"\s*:\s*(\d+)') {
        $FRONTEND_PORT = $matches[1]
    }
}

# Extract DASH API port (matching bash script pattern: PORT", [0-9]*)
if (Test-Path "$SCRIPT_DIR\services\DashSystem\dash_api.py") {
    $content = Get-Content "$SCRIPT_DIR\services\DashSystem\dash_api.py" -Raw
    if ($content -match 'PORT",\s*(\d+)') {
        $DASH_API_PORT = $matches[1]
    }
}

# Extract SherlockED API port (matching bash script pattern: PORT", [0-9]*)
if (Test-Path "$SCRIPT_DIR\services\SherlockEDApi\run_backend.py") {
    $content = Get-Content "$SCRIPT_DIR\services\SherlockEDApi\run_backend.py" -Raw
    if ($content -match 'PORT",\s*(\d+)') {
        $SHERLOCKED_API_PORT = $matches[1]
    }
}

# Extract TeachingAssistant port (matching bash script pattern: PORT", [0-9]*)
if (Test-Path "$SCRIPT_DIR\services\TeachingAssistant\api.py") {
    $content = Get-Content "$SCRIPT_DIR\services\TeachingAssistant\api.py" -Raw
    if ($content -match 'PORT",\s*(\d+)') {
        $TEACHING_ASSISTANT_PORT = $matches[1]
    }
}

# Extract Auth Service port (matching bash script pattern: PORT", [0-9]*)
if (Test-Path "$SCRIPT_DIR\services\AuthService\auth_api.py") {
    $content = Get-Content "$SCRIPT_DIR\services\AuthService\auth_api.py" -Raw
    if ($content -match 'PORT",\s*(\d+)') {
        $AUTH_SERVICE_PORT = $matches[1]
    }
}

# Start the Node.js frontend in the background
Write-Host "Starting Node.js frontend... Logs -> logs/frontend.log"
$proc = Start-Process -FilePath "cmd" -ArgumentList "/c", "npm run dev 2>&1" -WorkingDirectory "$SCRIPT_DIR\frontend" -NoNewWindow -PassThru -RedirectStandardOutput "$SCRIPT_DIR\logs\frontend.log"
$processes += $proc

$pids = $processes | ForEach-Object { $_.Id }
Write-Host "Tutor is running with the following PIDs: $($pids -join ', ')"
Write-Host ""
Write-Host "Service URLs:"
Write-Host "  Frontend:           http://localhost:$FRONTEND_PORT"
Write-Host "  Auth Service:       http://localhost:$AUTH_SERVICE_PORT"
Write-Host "  DASH API:           http://localhost:$DASH_API_PORT"
Write-Host "  SherlockED API:     http://localhost:$SHERLOCKED_API_PORT"
Write-Host "  TeachingAssistant:  http://localhost:$TEACHING_ASSISTANT_PORT"
Write-Host "  Tutor Service:      ws://localhost:8767"
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
                Write-Host "  Process $procId has exited"
            }
        }
    }
}
finally {
    # Handle Ctrl+C or script termination
    Cleanup
}
