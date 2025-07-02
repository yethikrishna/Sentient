<#
.SYNOPSIS
    Starts the frontend (Next.js) and backend (FastAPI) services for the Sentient project.

.DESCRIPTION
    This script runs:
    - The FastAPI backend server
    - The Next.js frontend client

    Both will be launched in separate PowerShell terminal windows with appropriate titles.

.NOTES
    - Run this from your project's root directory.
#>

# --- Configuration ---
$projectRoot = $PSScriptRoot
if (-not $projectRoot) { $projectRoot = Get-Location }

$srcPath = Join-Path $projectRoot "src"
$clientPath = Join-Path $srcPath "client"
$venvActivatePath = Join-Path $srcPath "server\venv\Scripts\activate.ps1"

# --- Validation ---
if (-not (Test-Path $clientPath)) { throw "Frontend directory 'src/client' not found." }
if (-not (Test-Path $venvActivatePath)) { throw "Virtual environment activation script not found at '$venvActivatePath'." }

Write-Host "✅ Paths verified." -ForegroundColor Green

# --- Helper Function ---
function Start-NewTerminal {
    param (
        [string]$WindowTitle,
        [string]$Command,
        [string]$WorkDir = $projectRoot
    )
    $psCommand = "Set-Location -Path '$WorkDir'; `$Host.UI.RawUI.WindowTitle = '$WindowTitle'; $Command"
    Start-Process powershell.exe -ArgumentList "-NoExit", "-Command", $psCommand -WorkingDirectory $WorkDir
}

# --- Start Backend ---
Write-Host "🚀 Launching FastAPI Backend..." -ForegroundColor Yellow
$backendCommand = "& '$venvActivatePath'; python -m server.main.app"
Start-NewTerminal -WindowTitle "API - Main Server" -Command $backendCommand -WorkDir $srcPath

# --- Start Frontend ---
Write-Host "🚀 Launching Next.js Frontend..." -ForegroundColor Yellow
Start-NewTerminal -WindowTitle "CLIENT - Next.js" -Command "npm run dev" -WorkDir $clientPath

Write-Host "`n✅ Frontend and backend launched successfully in new terminals." -ForegroundColh

Write-Host "`n✅ Frontend and backend launcoed successfully in new terminals." -ForegroundColor Greenr Green
