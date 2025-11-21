# Get the directory where the script is located
$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $SCRIPT_DIR

# Clean up old logs and create a fresh logs directory
if (Test-Path "$SCRIPT_DIR\logs") {
    Remove-Item -Recurse -Force "$SCRIPT_DIR\logs"
}
New-Item -ItemType Directory -Path "$SCRIPT_DIR\logs" -Force | Out-Null

# Detect Python environment
$VENV_PATH = $null
if ($env:VIRTUAL_ENV) {
    Write-Host "Using already active virtual environment: $env:VIRTUAL_ENV" -ForegroundColor Green
    $PYTHON_BIN = "python"
} elseif (Test-Path "$SCRIPT_DIR\env\Scripts\Activate.ps1") {
    Write-Host "Activating local env..." -ForegroundColor Yellow
    & "$SCRIPT_DIR\env\Scripts\Activate.ps1"
    $PYTHON_BIN = "$SCRIPT_DIR\env\Scripts\python.exe"
} elseif (Test-Path "$SCRIPT_DIR\.env\Scripts\Activate.ps1") {
    Write-Host "Activating local .env..." -ForegroundColor Yellow
    & "$SCRIPT_DIR\.env\Scripts\Activate.ps1"
    $PYTHON_BIN = "$SCRIPT_DIR\.env\Scripts\python.exe"
} else {
    Write-Host "❌ No virtual environment found." -ForegroundColor Red
    Write-Host "👉 Please create one with:" -ForegroundColor Yellow
    Write-Host "    python -m venv env" -ForegroundColor Cyan
    Write-Host "    .\env\Scripts\Activate.ps1" -ForegroundColor Cyan
    Write-Host "👉 Next, install the required packages with:" -ForegroundColor Yellow
    Write-Host "    pip install -r requirements.txt" -ForegroundColor Cyan
    Write-Host "👉 If you plan to use the frontend, also run:" -ForegroundColor Yellow
    Write-Host "    cd frontend" -ForegroundColor Cyan
    Write-Host "    npm install --force" -ForegroundColor Cyan
    Write-Host "    cd .." -ForegroundColor Cyan
    Write-Host "👉 Finally, run this script again." -ForegroundColor Yellow
    exit 1
}

Write-Host "Using Python: $PYTHON_BIN" -ForegroundColor Green

# Array to hold the background jobs
$jobs = @()

# Function to clean up background processes
function Cleanup {
    Write-Host "`nShutting down tutor..." -ForegroundColor Yellow
    foreach ($job in $jobs) {
        if ($job.State -eq "Running") {
            Write-Host "Stopping job: $($job.Name)" -ForegroundColor Yellow
            Stop-Job -Job $job -ErrorAction SilentlyContinue
            Remove-Job -Job $job -ErrorAction SilentlyContinue
        }
    }
    # Also kill any remaining Python/node processes
    Get-Process python, node -ErrorAction SilentlyContinue | Where-Object { $_.Path -like "*$SCRIPT_DIR*" } | Stop-Process -Force -ErrorAction SilentlyContinue
    Write-Host "All processes terminated." -ForegroundColor Green
}

# Register cleanup on Ctrl+C
[Console]::TreatControlCAsInput = $false
$null = Register-EngineEvent PowerShell.Exiting -Action { Cleanup }

# Start the Python backend in the background
Write-Host "Starting Python backend... Logs -> logs/mediamixer.log" -ForegroundColor Cyan
$job1 = Start-Job -Name "MediaMixer" -ScriptBlock {
    param($dir, $python)
    Set-Location $dir
    & $python MediaMixer/media_mixer.py *> "$dir\logs\mediamixer.log"
} -ArgumentList $SCRIPT_DIR, $PYTHON_BIN
$jobs += $job1

# Start the FastAPI server in the background
Write-Host "Starting DASH API server... Logs -> logs/api.log" -ForegroundColor Cyan
$job2 = Start-Job -Name "DASH_API" -ScriptBlock {
    param($dir, $python)
    Set-Location $dir
    & $python DashSystem/dash_api.py *> "$dir\logs\api.log"
} -ArgumentList $SCRIPT_DIR, $PYTHON_BIN
$jobs += $job2

# Start the SherlockEDExam FastAPI server in the background
Write-Host "Starting SherlockED Exam API server... Logs -> logs/sherlocked_exam.log" -ForegroundColor Cyan
$job3 = Start-Job -Name "SherlockED_API" -ScriptBlock {
    param($dir, $python)
    Set-Location $dir
    & $python SherlockEDApi/run_backend.py *> "$dir\logs\sherlocked_exam.log"
} -ArgumentList $SCRIPT_DIR, $PYTHON_BIN
$jobs += $job3

# Start the TeachingAssistant API server in the background
Write-Host "Starting TeachingAssistant API server... Logs -> logs/teaching_assistant.log" -ForegroundColor Cyan
$job4 = Start-Job -Name "TeachingAssistant" -ScriptBlock {
    param($dir, $python)
    Set-Location $dir
    & $python TeachingAssistant/api.py *> "$dir\logs\teaching_assistant.log"
} -ArgumentList $SCRIPT_DIR, $PYTHON_BIN
$jobs += $job4

# Give the backend servers a moment to start
Write-Host "Waiting for backend services to initialize..." -ForegroundColor Yellow
Start-Sleep -Seconds 2

# Extract ports (defaults if parsing fails)
$FRONTEND_PORT = 3000
$DASH_API_PORT = 8000
$SHERLOCKED_API_PORT = 8001
$TEACHING_ASSISTANT_PORT = 8002
$MEDIAMIXER_COMMAND_PORT = 8765
$MEDIAMIXER_VIDEO_PORT = 8766

# Try to extract ports from config files
if (Test-Path "$SCRIPT_DIR\frontend\vite.config.ts") {
    $viteConfig = Get-Content "$SCRIPT_DIR\frontend\vite.config.ts" -Raw
    if ($viteConfig -match 'port:\s*(\d+)') {
        $FRONTEND_PORT = [int]$matches[1]
    }
}

if (Test-Path "$SCRIPT_DIR\DashSystem\dash_api.py") {
    $dashApi = Get-Content "$SCRIPT_DIR\DashSystem\dash_api.py" -Raw
    if ($dashApi -match 'port=(\d+)') {
        $DASH_API_PORT = [int]$matches[1]
    }
}

if (Test-Path "$SCRIPT_DIR\SherlockEDApi\run_backend.py") {
    $sherlockedApi = Get-Content "$SCRIPT_DIR\SherlockEDApi\run_backend.py" -Raw
    if ($sherlockedApi -match 'port=(\d+)') {
        $SHERLOCKED_API_PORT = [int]$matches[1]
    }
}

# Start the Node.js frontend in the background
Write-Host "Starting Node.js frontend... Logs -> logs/frontend.log" -ForegroundColor Cyan
$job5 = Start-Job -Name "Frontend" -ScriptBlock {
    param($dir)
    Set-Location "$dir\frontend"
    npm run dev *> "$dir\logs\frontend.log"
} -ArgumentList $SCRIPT_DIR
$jobs += $job5

Write-Host ""
Write-Host "Tutor is running with the following jobs:" -ForegroundColor Green
foreach ($job in $jobs) {
    Write-Host "  - $($job.Name) (ID: $($job.Id))" -ForegroundColor Cyan
}
Write-Host ""
Write-Host "📡 Service URLs:" -ForegroundColor Green
Write-Host "  🌐 Frontend:           http://localhost:$FRONTEND_PORT" -ForegroundColor White
Write-Host "  🔧 DASH API:           http://localhost:$DASH_API_PORT" -ForegroundColor White
Write-Host "  🕵️  SherlockED API:     http://localhost:$SHERLOCKED_API_PORT" -ForegroundColor White
Write-Host "  👨‍🏫 TeachingAssistant:  http://localhost:$TEACHING_ASSISTANT_PORT" -ForegroundColor White
Write-Host "  📹 MediaMixer Command: ws://localhost:$MEDIAMIXER_COMMAND_PORT" -ForegroundColor White
Write-Host "  📺 MediaMixer Video:   ws://localhost:$MEDIAMIXER_VIDEO_PORT" -ForegroundColor White
Write-Host ""
Write-Host "Press Ctrl+C to stop." -ForegroundColor Yellow
Write-Host "You can view the logs for each service in the 'logs' directory." -ForegroundColor Gray
Write-Host ""

# Wait for user interrupt
try {
    while ($true) {
        Start-Sleep -Seconds 1
        # Check if any job has failed
        foreach ($job in $jobs) {
            if ($job.State -eq "Failed") {
                Write-Host "Warning: Job $($job.Name) has failed. Check logs for details." -ForegroundColor Red
            }
        }
    }
} catch {
    # Handle Ctrl+C
} finally {
    Cleanup
}