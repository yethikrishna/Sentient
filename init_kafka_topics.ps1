<#
.SYNOPSIS
    Initializes Kafka topics for the Sentient project.

.DESCRIPTION
    This script runs the kafka_topic_initializer module from your backend,
    using the existing virtual environment, in a transient PowerShell window.
#>

# --- Configuration ---
$projectRoot = $PSScriptRoot
if (-not $projectRoot) { $projectRoot = Get-Location }

$srcPath = Join-Path $projectRoot "src"
$venvActivatePath = Join-Path $srcPath "server\venv\Scripts\activate.ps1"

# Validation
if (-not (Test-Path $venvActivatePath)) {
    throw "Virtual environment activation script not found at '$venvActivatePath'."
}

Write-Host "✅ Kafka topic initialization paths verified." -ForegroundColor Green

# --- Run Kafka Topic Initializer ---
$command = "& '$venvActivatePath'; python -m server.workers.utils.kafka_topic_initializer"
$psCommand = "Set-Location -Path '$srcPath'; $command"

Write-Host "🚀 Initializing Kafka topics..." -ForegroundColor Cyan

Start-Process powershell.exe -ArgumentList "-Command", $psCommand -WorkingDirectory $srcPath

Write-Host "✅ Kafka topic initialization launched in background." -ForegroundColor Green
