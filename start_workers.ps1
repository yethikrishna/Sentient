<#
.SYNOPSIS
    Starts only the backend workers for the Sentient project.

.DESCRIPTION
    This script launches the Celery worker and the Celery Beat scheduler,
    each in their own terminal window, using your Python virtual environment.
#>

# --- Configuration ---
$projectRoot = $PSScriptRoot
if (-not $projectRoot) { $projectRoot = Get-Location }

$srcPath = Join-Path -Path $projectRoot -ChildPath "src"
$serverPath = Join-Path -Path $srcPath -ChildPath "server"
$venvActivatePath = Join-Path -Path $serverPath -ChildPath "venv\Scripts\activate.ps1"

# Validate required paths
if (-not (Test-Path -Path $srcPath)) { throw "'src' directory not found." }
if (-not (Test-Path -Path $serverPath)) { throw "'src/server' directory not found." }
if (-not (Test-Path -Path $venvActivatePath)) { throw "Virtual environment not found at '$venvActivatePath'." }

Write-Host "✅ Worker paths verified." -ForegroundColor Green

# Helper: Launch PowerShell in new terminal
function Start-NewTerminal {
    param(
        [string]$WindowTitle,
        [string]$Command,
        [string]$WorkDir = $projectRoot
    )
    $psCommand = "Set-Location -Path '$WorkDir'; `$Host.UI.RawUI.WindowTitle = '$WindowTitle'; $Command"
    Start-Process powershell.exe -ArgumentList "-NoExit", "-Command", $psCommand -WorkingDirectory $WorkDir
}

# --- Start Worker Services ---
Write-Host "`n🚀 Starting Backend Workers..." -ForegroundColor Cyan

$workerServices = @(
    @{ Name = "Celery Worker"; Command = "& '$venvActivatePath'; celery -A workers.celery_app worker --loglevel=info --pool=solo" },
    @{ Name = "Celery Beat Scheduler"; Command = "& '$venvActivatePath'; celery -A workers.celery_app beat --loglevel=info" }
)

foreach ($service in $workerServices) {
    $windowTitle = "WORKER - $($service.Name)"
    Write-Host "🟢 Launching $windowTitle..." -ForegroundColor Yellow
    Start-NewTerminal -WindowTitle $windowTitle -Command $service.Command -WorkDir $serverPath
    Start-Sleep -Milliseconds 500
}

Write-Host "`n✅ All backend workers launched successfully." -ForegroundColor Green