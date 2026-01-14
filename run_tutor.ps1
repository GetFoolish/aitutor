<#
.SYNOPSIS
    Startup script for AI Tutor application (Windows PowerShell)
.DESCRIPTION
    Loads environment variables, activates Python venv, starts backend services, and launches frontend.
#>

$ErrorActionPreference = "Continue"
$ScriptDir = $PSScriptRoot

# 1. Load .env file
$EnvFile = Join-Path $ScriptDir ".env"
if (Test-Path $EnvFile) {
    Write-Host "Loading environment variables from .env..." -ForegroundColor Cyan
    Get-Content $EnvFile | ForEach-Object {
        if ($_ -match '^\s*([^#=]+)\s*=\s*(.*)$') {
            $Key = $Matches[1].Trim()
            $Value = $Matches[2].Trim().Trim('"').Trim("'")
            # Defensively strip CR/LF characters that can sneak in via copy/paste
            $Value = $Value -replace "[`r`n]", ""
            if (-not [string]::IsNullOrWhiteSpace($Key)) {
                [System.Environment]::SetEnvironmentVariable($Key, $Value, [System.EnvironmentVariableTarget]::Process)
                Write-Host "  Loaded: $Key" -ForegroundColor DarkGray
            }
        }
    }
}
else {
    Write-Host "⚠️  No .env file found. Using defaults." -ForegroundColor Yellow
}

# Ensure Python services use UTF-8 for stdout/stderr to avoid UnicodeEncodeError on Windows consoles
[System.Environment]::SetEnvironmentVariable("PYTHONUTF8", "1", [System.EnvironmentVariableTarget]::Process)
[System.Environment]::SetEnvironmentVariable("PYTHONIOENCODING", "utf-8", [System.EnvironmentVariableTarget]::Process)

# 2. Setup Logs Directory
$LogDir = Join-Path $ScriptDir "logs"
if (Test-Path $LogDir) { Remove-Item $LogDir -Recurse -Force -ErrorAction SilentlyContinue }
New-Item -ItemType Directory -Path $LogDir -Force | Out-Null

# 3. Detect Python Environment
$PythonBin = "python"
if ($env:VIRTUAL_ENV) {
    $PythonBin = Join-Path $env:VIRTUAL_ENV "Scripts\python.exe"
}
elseif (Test-Path "$ScriptDir\env\Scripts\python.exe") {
    $PythonBin = "$ScriptDir\env\Scripts\python.exe"
    $env:VIRTUAL_ENV = "$ScriptDir\env"
}
elseif (Test-Path "$ScriptDir\.env\Scripts\python.exe") {
    $PythonBin = "$ScriptDir\.env\Scripts\python.exe"
    $env:VIRTUAL_ENV = "$ScriptDir\.env"
}
elseif (Test-Path "$ScriptDir\.venv\Scripts\python.exe") {
    $PythonBin = "$ScriptDir\.venv\Scripts\python.exe"
    $env:VIRTUAL_ENV = "$ScriptDir\.venv"
}
else {
    Write-Host "❌ No virtual environment found. Please create one with 'python -m venv env'" -ForegroundColor Red
    exit 1
}

Write-Host "Using Python: $PythonBin" -ForegroundColor Cyan

# 4. Start Services
$Jobs = @()

function Stop-ListeningProcessesOnPort {
    param(
        [Parameter(Mandatory = $true)][int]$Port
    )

    $processIds = @()
    try {
        $processIds = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction Stop |
        Select-Object -ExpandProperty OwningProcess -Unique
    }
    catch {
        # Fallback for environments where Get-NetTCPConnection isn't available
        $processIds = netstat -ano | Select-String ":$Port\s+LISTENING\s+(\d+)$" | ForEach-Object {
            [int]$_.Matches[0].Groups[1].Value
        } | Select-Object -Unique
    }

    foreach ($procId in $processIds) {
        if (-not $procId -or $procId -eq 0) { continue }
        try {
            $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
            if ($proc) {
                Write-Host "Stopping process $($proc.ProcessName) (PID $procId) on port $Port..." -ForegroundColor Yellow
            }
            else {
                Write-Host "Stopping PID $procId on port $Port..." -ForegroundColor Yellow
            }
            Stop-Process -Id $procId -Force -ErrorAction Stop
        }
        catch {
            Write-Host "⚠️  Could not stop PID $procId on port ${Port}: $($_.Exception.Message)" -ForegroundColor DarkYellow
        }
    }
}

# Preflight: clear stale listeners so the stack can start cleanly
Stop-ListeningProcessesOnPort -Port 3000
Stop-ListeningProcessesOnPort -Port 8000
Stop-ListeningProcessesOnPort -Port 8001
Stop-ListeningProcessesOnPort -Port 8002
Stop-ListeningProcessesOnPort -Port 8003

function Start-ServiceBackground {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$ScriptPath,
        [string]$ScriptArgs = "",
        [Parameter(Mandatory = $true)][string]$LogFile
    )
    Write-Host "Starting $Name..." -ForegroundColor Green
    $Job = Start-Job -Name $Name -ScriptBlock {
        param($PythonBin, $ScriptDir, $ScriptPath, $ScriptArgs, $LogFile)
        Set-Location $ScriptDir
        # Merge stderr into stdout so we can surface tracebacks in the monitor loop
        $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        "[$timestamp] Starting: $PythonBin $ScriptPath $ScriptArgs" | Out-File -FilePath $LogFile -Encoding utf8 -Append
        if ($ScriptArgs) {
            & $PythonBin $ScriptPath $ScriptArgs 2>&1 | Tee-Object -FilePath $LogFile -Append
        }
        else {
            & $PythonBin $ScriptPath 2>&1 | Tee-Object -FilePath $LogFile -Append
        }
    } -ArgumentList $PythonBin, $ScriptDir, $ScriptPath, $ScriptArgs, $LogFile
    return $Job
}

# Dash API
$Jobs += Start-ServiceBackground -Name "DASH API" -ScriptPath "services\DashSystem\dash_api.py" -LogFile (Join-Path $LogDir "dash_api.log")

# SherlockED API
$Jobs += Start-ServiceBackground -Name "SherlockED API" -ScriptPath "services\SherlockEDApi\run_backend.py" -LogFile (Join-Path $LogDir "sherlocked_api.log")

# Auth Service
$Jobs += Start-ServiceBackground -Name "Auth Service" -ScriptPath "services\AuthService\auth_api.py" -LogFile (Join-Path $LogDir "auth_service.log")

# LiveKit Agent
$Jobs += Start-ServiceBackground -Name "LiveKit Agent" -ScriptPath "services\LiveKitAgent\agent.py" -ScriptArgs "dev" -LogFile (Join-Path $LogDir "livekit_agent.log")

# TeachingAssistant API
$Jobs += Start-ServiceBackground -Name "TeachingAssistant API" -ScriptPath "services\TeachingAssistant\api.py" -LogFile (Join-Path $LogDir "teaching_assistant_api.log")

Write-Host "Waiting for backend services to initialize..." -ForegroundColor Cyan
Start-Sleep -Seconds 3

# 5. Start Frontend
Write-Host "Starting Frontend..." -ForegroundColor Green
# On Windows, npm is a script (npm.cmd), so we must point to it explicitly or use cmd /c
$NpmCmd = Get-Command npm.cmd -ErrorAction SilentlyContinue
if ($NpmCmd) {
    $FrontendProcess = Start-Process -FilePath "npm.cmd" -ArgumentList "run dev" -WorkingDirectory "$ScriptDir\frontend" -PassThru -NoNewWindow -RedirectStandardOutput (Join-Path $LogDir "frontend.log") -RedirectStandardError (Join-Path $LogDir "frontend.err.log")
}
else {
    # Fallback usually works if npm is in path but checking explicitly is safer
    $FrontendProcess = Start-Process -FilePath "npm" -ArgumentList "run dev" -WorkingDirectory "$ScriptDir\frontend" -PassThru -NoNewWindow -RedirectStandardOutput (Join-Path $LogDir "frontend.log") -RedirectStandardError (Join-Path $LogDir "frontend.err.log")
}

Write-Host "`nAll services started. Press Ctrl+C to stop.`n" -ForegroundColor Green

# 6. Monitor Loop
try {
    $ReportedStoppedJobs = @{}
    while ($true) {
        if ($FrontendProcess.HasExited) {
            Write-Host "Frontend exited. Shutting down..." -ForegroundColor Yellow
            break
        }
        
        # Check if backend jobs are still running
        foreach ($Job in @($Jobs)) {
            # Check for output and print it (non-blocking)
            if ($Job.HasMoreData) {
                Receive-Job $Job | ForEach-Object { Write-Host "[$($Job.Name)] $_" -ForegroundColor Gray }
            }

            if ($Job.State -ne 'Running') {
                if (-not $ReportedStoppedJobs.ContainsKey($Job.Id)) {
                    $ReportedStoppedJobs[$Job.Id] = $true
                    Write-Host "Service $($Job.Id) ($($Job.Name)) stopped unexpectedly." -ForegroundColor Red
                    # Receive remaining output once
                    Receive-Job $Job | ForEach-Object { Write-Host "[$($Job.Name)] $_" -ForegroundColor Gray }
                    # Remove job from active watch list so we don't spam the same message
                    $Jobs = @($Jobs | Where-Object { $_.Id -ne $Job.Id })
                }
            }
        }
        Start-Sleep -Milliseconds 500
    }
}
finally {
    Write-Host "Stopping all services..." -ForegroundColor Yellow
    foreach ($Job in $Jobs) { Stop-Job $Job -ErrorAction SilentlyContinue; Remove-Job $Job -ErrorAction SilentlyContinue }
    if (-not $FrontendProcess.HasExited) { Stop-Process -Id $FrontendProcess.Id -ErrorAction SilentlyContinue }
}
