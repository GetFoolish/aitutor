<#
.SYNOPSIS
    Startup script for AI Tutor application (Windows PowerShell)
.DESCRIPTION
    Loads environment variables, activates Python venv, starts backend services, and launches frontend.
#>

$ErrorActionPreference = "Stop"
$ScriptDir = $PSScriptRoot

# 1. Load .env file
$EnvFile = Join-Path $ScriptDir ".env"
if (Test-Path $EnvFile) {
    Write-Host "Loading environment variables from .env..." -ForegroundColor Cyan
    Get-Content $EnvFile | ForEach-Object {
        if ($_ -match '^\s*([^#=]+)\s*=\s*(.*)$') {
            $Key = $Matches[1].Trim()
            $Value = $Matches[2].Trim().Trim('"').Trim("'")
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

function Start-ServiceBackground {
    param($Name, $ScriptPath, $LogFile)
    Write-Host "Starting $Name..." -ForegroundColor Green
    $Job = Start-Job -ScriptBlock {
        param($PythonBin, $ScriptDir, $ScriptPath)
        Set-Location $ScriptDir
        & $PythonBin $ScriptPath
    } -ArgumentList $PythonBin, $ScriptDir, $ScriptPath
    return $Job
}

# Dash API
$Jobs += Start-ServiceBackground "DASH API" "services\DashSystem\dash_api.py"

# SherlockED API
$Jobs += Start-ServiceBackground "SherlockED API" "services\SherlockEDApi\run_backend.py"

# TeachingAssistant API
$Jobs += Start-ServiceBackground "TeachingAssistant API" "services\TeachingAssistant\api.py"

# Auth Service
$Jobs += Start-ServiceBackground "Auth Service" "services\AuthService\auth_api.py"

Write-Host "Waiting for backend services to initialize..." -ForegroundColor Cyan
Start-Sleep -Seconds 3

# 5. Start Frontend
Write-Host "Starting Frontend..." -ForegroundColor Green
# On Windows, npm is a script (npm.cmd), so we must point to it explicitly or use cmd /c
$NpmCmd = Get-Command npm.cmd -ErrorAction SilentlyContinue
if ($NpmCmd) {
    $FrontendProcess = Start-Process -FilePath "npm.cmd" -ArgumentList "run dev" -WorkingDirectory "$ScriptDir\frontend" -PassThru -NoNewWindow
}
else {
    # Fallback usually works if npm is in path but checking explicitly is safer
    $FrontendProcess = Start-Process -FilePath "npm" -ArgumentList "run dev" -WorkingDirectory "$ScriptDir\frontend" -PassThru -NoNewWindow
}

Write-Host "`nAll services started. Press Ctrl+C to stop.`n" -ForegroundColor Green

# 6. Monitor Loop
try {
    while ($true) {
        if ($FrontendProcess.HasExited) {
            Write-Host "Frontend exited. Shutting down..." -ForegroundColor Yellow
            break
        }
        
        # Check if backend jobs are still running
        foreach ($Job in $Jobs) {
            if ($Job.State -ne 'Running') {
                Write-Host "Service $($Job.Id) stopped unexpectedly." -ForegroundColor Red
                Receive-Job $Job | Write-Host
            }
        }
        Start-Sleep -Seconds 1
    }
}
finally {
    Write-Host "Stopping all services..." -ForegroundColor Yellow
    foreach ($Job in $Jobs) { Stop-Job $Job -ErrorAction SilentlyContinue; Remove-Job $Job -ErrorAction SilentlyContinue }
    if (-not $FrontendProcess.HasExited) { Stop-Process -Id $FrontendProcess.Id -ErrorAction SilentlyContinue }
}
