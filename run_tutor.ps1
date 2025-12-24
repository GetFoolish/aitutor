<#
.SYNOPSIS
    Starts the AI Tutor platform (Backend Services + Frontend) on Windows without Docker.
.DESCRIPTION
    This script automates the process of running the AI Tutor platform locally.
    It performs the following:
    1. Checks for and loads environment variables from .env
    2. Detects and activates the Python virtual environment
    3. Starts all backend microservices (DASH, SherlockED, Auth, TeachingAssistant) in the background
    4. Starts the frontend development server
    5. Monitors processes and handles graceful shutdown (Ctrl+C)
.NOTES
    Run this script from the project root.
    Ensure you have created a .env file and installed dependencies (pip install -r requirements.txt).
#>

$ErrorActionPreference = "Stop"
$ScriptDir = $PSScriptRoot
$LogDir = Join-Path $ScriptDir "logs"

# --- 1. Setup Logs Directory ---
if (Test-Path $LogDir) {
    Remove-Item $LogDir -Recurse -Force
}
New-Item -ItemType Directory -Path $LogDir | Out-Null
Write-Host "[+] Logs directory created at: $LogDir" -ForegroundColor Cyan

# --- 2. Load Environment Variables ---
$EnvFile = Join-Path $ScriptDir ".env"
if (Test-Path $EnvFile) {
    Write-Host "[*] Loading environment variables from .env..." -ForegroundColor Cyan
    Get-Content $EnvFile | ForEach-Object {
        $line = $_.Trim()
        if ($line -and -not $line.StartsWith("#")) {
            $parts = $line -split "=", 2
            if ($parts.Length -eq 2) {
                $name = $parts[0].Trim()
                $value = $parts[1].Trim().Trim('"').Trim("'")
                [System.Environment]::SetEnvironmentVariable($name, $value, [System.EnvironmentVariableTarget]::Process)
            }
        }
    }
    Write-Host "[OK] Environment variables loaded." -ForegroundColor Green
}
else {
    Write-Warning "[WARN] No .env file found. Using default values. Please create one for full functionality."
}

# --- 3. Detect Python Environment ---
$PythonExe = "python"
$VenvPath = $null

if ($env:VIRTUAL_ENV) {
    $VenvPath = $env:VIRTUAL_ENV
    Write-Host "[OK] Using active virtual environment: $VenvPath" -ForegroundColor Green
}
elseif (Test-Path (Join-Path $ScriptDir ".venv")) {
    $VenvPath = Join-Path $ScriptDir ".venv"
}
elseif (Test-Path (Join-Path $ScriptDir "env")) {
    $VenvPath = Join-Path $ScriptDir "env"
}

if ($VenvPath) {
    $PythonExe = Join-Path $VenvPath "Scripts\python.exe"
    if (-not (Test-Path $PythonExe)) {
        # Fallback for some windows venv structures
        $PythonExe = Join-Path $VenvPath "bin\python"
        if (-not (Test-Path $PythonExe)) {
            Write-Warning "[WARN] Found venv at $VenvPath but could not find python executable. Using system python."
            $PythonExe = "python"
        }
    }
}
else {
    Write-Warning "[WARN] No virtual environment found. Using system python."
    Write-Host "[TIP] Recommendation: python -m venv .venv; .\.venv\Scripts\Activate.ps1" -ForegroundColor Yellow
}

Write-Host "[Python] Using Python: $PythonExe" -ForegroundColor Cyan

# --- 4. Start Backend Services ---
$Jobs = @()

function Start-ServiceProcess {
    param (
        [string]$Name,
        [string]$ScriptPath,
        [string]$LogName,
        [int]$Port
    )
    
    Write-Host "[START] Starting $Name on port $Port..." -ForegroundColor Cyan
    
    $LogPath = Join-Path $LogDir $LogName
    
    # We use Start-Process to run in background.
    # Note: Redirecting stdout/stderr directly in Start-Process is tricky with real-time logging in PS.
    # We simply start it. To view logs, user uses the log files.
    
    $ProcessInfo = New-Object System.Diagnostics.ProcessStartInfo
    $ProcessInfo.FileName = $PythonExe
    $ProcessInfo.Arguments = "$ScriptPath"
    $ProcessInfo.WorkingDirectory = $ScriptDir
    $ProcessInfo.RedirectStandardOutput = $true
    $ProcessInfo.RedirectStandardError = $true
    $ProcessInfo.UseShellExecute = $false
    $ProcessInfo.CreateNoWindow = $true

    $Process = New-Object System.Diagnostics.Process
    $Process.StartInfo = $ProcessInfo

    # Event handlers to capture output to files
    $ActionOut = { 
        if ($Event.SourceEventArgs.Data) { 
            Add-Content -Path $Event.MessageData -Value $Event.SourceEventArgs.Data 
        } 
    }
    
    Register-ObjectEvent -InputObject $Process -EventName OutputDataReceived -Action $ActionOut -MessageData $LogPath | Out-Null
    Register-ObjectEvent -InputObject $Process -EventName ErrorDataReceived -Action $ActionOut -MessageData $LogPath | Out-Null

    $Process.Start() | Out-Null
    $Process.BeginOutputReadLine()
    $Process.BeginErrorReadLine()

    return $Process
}

$Services = @(
    @{ Name = "DASH API"; Script = "services/DashSystem/dash_api.py"; Log = "dash_api.log"; Port = 8000 },
    @{ Name = "SherlockED API"; Script = "services/SherlockEDApi/run_backend.py"; Log = "sherlocked_exam.log"; Port = 8001 },
    @{ Name = "Teaching Assistant"; Script = "services/TeachingAssistant/api.py"; Log = "teaching_assistant.log"; Port = 8002 },
    @{ Name = "Auth Service"; Script = "services/AuthService/auth_api.py"; Log = "auth_service.log"; Port = 8003 }
)

foreach ($Svc in $Services) {
    try {
        $Proc = Start-ServiceProcess -Name $Svc.Name -ScriptPath $Svc.Script -LogName $Svc.Log -Port $Svc.Port
        $Jobs += $Proc
    }
    catch {
        Write-Error "Failed to start $($Svc.Name): $_"
    }
}

# --- 5. Start Frontend ---
Write-Host "[START] Starting Frontend..." -ForegroundColor Cyan
$FrontendLog = Join-Path $LogDir "frontend.log"
$FrontendProcessInfo = New-Object System.Diagnostics.ProcessStartInfo
$FrontendProcessInfo.FileName = "cmd.exe"
$FrontendProcessInfo.Arguments = "/c npm run dev"
$FrontendProcessInfo.WorkingDirectory = Join-Path $ScriptDir "frontend"
$FrontendProcessInfo.RedirectStandardOutput = $true
$FrontendProcessInfo.RedirectStandardError = $true
$FrontendProcessInfo.UseShellExecute = $false
$FrontendProcessInfo.CreateNoWindow = $true

$FrontendProcess = New-Object System.Diagnostics.Process
$FrontendProcess.StartInfo = $FrontendProcessInfo

# Capture Frontend Logs
$ActionOutFE = { 
    if ($Event.SourceEventArgs.Data) { 
        Add-Content -Path $Event.MessageData -Value $Event.SourceEventArgs.Data 
    } 
}
Register-ObjectEvent -InputObject $FrontendProcess -EventName OutputDataReceived -Action $ActionOutFE -MessageData $FrontendLog | Out-Null
Register-ObjectEvent -InputObject $FrontendProcess -EventName ErrorDataReceived -Action $ActionOutFE -MessageData $FrontendLog | Out-Null

$FrontendProcess.Start() | Out-Null
$FrontendProcess.BeginOutputReadLine()
$FrontendProcess.BeginErrorReadLine()
$Jobs += $FrontendProcess

# --- 6. Monitoring and Cleanup ---
Write-Host "`n[OK] All services started!" -ForegroundColor Green
Write-Host "[INFO] Service URLs:"
Write-Host "  [Web] Frontend:           http://localhost:3000"
Write-Host "  [Auth] Auth Service:       http://localhost:8003"
Write-Host "  [API] DASH API:           http://localhost:8000"
Write-Host "  [API] SherlockED API:     http://localhost:8001"
Write-Host "  [API] TeachingAssistant:  http://localhost:8002"
Write-Host "`n[Logs] Logs are being written to: $LogDir"
Write-Host "[STOP] Press 'Q' then Enter to stop all services..." -ForegroundColor Yellow

# Loop to keep script running
try {
    while ($true) {
        if ([Console]::KeyAvailable) {
            $key = [Console]::ReadKey($true)
            if ($key.Key -eq 'Q') {
                break
            }
        }
        Start-Sleep -Milliseconds 500
        
        # Check if processes are still alive
        foreach ($Proc in $Jobs) {
            if ($Proc.HasExited) {
                Write-Warning "[WARN] A service process (ID: $($Proc.Id)) has exited unexpectedly. Check logs."
                $Jobs = $Jobs | Where-Object { $_.Id -ne $Proc.Id }
            }
        }
    }
}
finally {
    Write-Host "`n[STOP] Stopping all services..." -ForegroundColor Yellow
    foreach ($Proc in $Jobs) {
        if (-not $Proc.HasExited) {
            Stop-Process -Id $Proc.Id -Force -ErrorAction SilentlyContinue
            Write-Host "   Killed process $($Proc.Id)"
        }
    }
    Write-Host "[DONE] Setup complete." -ForegroundColor Green
}
