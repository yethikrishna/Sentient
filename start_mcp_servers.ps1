<#
.SYNOPSIS
    Starts only the MCP servers for the Sentient project.

.DESCRIPTION
    This script dynamically discovers and starts all MCP servers
    located in src/server/mcp_hub in separate PowerShell terminals.
#>

# --- Configuration ---
$projectRoot = $PSScriptRoot
if (-not $projectRoot) { $projectRoot = Get-Location }

$srcPath = Join-Path -Path $projectRoot -ChildPath "src"
$mcpHubPath = Join-Path -Path $srcPath -ChildPath "server\mcp_hub"
$venvActivatePath = Join-Path -Path $srcPath -ChildPath "server\venv\Scripts\activate.ps1"

# Validate paths
if (-not (Test-Path -Path $mcpHubPath)) { throw "The 'src/server/mcp_hub' directory was not found." }
if (-not (Test-Path -Path $venvActivatePath)) { throw "The venv activation script was not found at '$venvActivatePath'." }

Write-Host "✅ MCP server paths verified." -ForegroundColor Green

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

# --- Start MCP Servers ---
Write-Host "`n🚀 Starting MCP Servers..." -ForegroundColor Cyan
$mcpServers = Get-ChildItem -Path $mcpHubPath -Directory | Select-Object -ExpandProperty Name
if ($mcpServers.Count -eq 0) { throw "No MCP servers found in '$mcpHubPath'." }

foreach ($serverName in $mcpServers) {
    $windowTitle = "MCP - $($serverName.ToUpper())"
    $pythonModule = "server.mcp_hub.$serverName.main"
    $commandToRun = "& '$venvActivatePath'; python -m '$pythonModule'"
    Write-Host "🟢 Launching $windowTitle..." -ForegroundColor Yellow
    Start-NewTerminal -WindowTitle $windowTitle -Command $commandToRun -WorkDir $srcPath
    Start-Sleep -Milliseconds 500
}

W

Write-Host "`n✅ All MCP servers launched successfully." -ForegroundColor Greenrite-Host "`n✅ All MCP servers launched successfully." -ForegroundColor Green
