# Filename: start_mcps.ps1
# Place this script in the root of your project (e.g., D:\Documents\cyber\projects\Sentient-New\Code)

<#
.SYNOPSIS
    Starts all or selected MCP (Modular Companion Protocol) servers in separate PowerShell windows.

.DESCRIPTION
    This script automates the process of launching the various Python-based MCP servers for the Sentient project.
    It locates all MCP server directories, then for each server:
    1. Opens a new, independent PowerShell terminal window.
    2. Sets the title of the new window to the server's name (e.g., "MCP - GMAIL").
    3. Changes the working directory to the 'src' folder.
    4. Activates the Python virtual environment.
    5. Executes the server's main.py using 'python -m'.

.NOTES
    - Ensure you have a virtual environment located at '.\src\server\venv\'.
    - To run this script, you may need to adjust your PowerShell execution policy.
      Open PowerShell as an Administrator and run:
      Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
#>

# --- Configuration ---
# The script automatically finds all directories inside 'src\server\mcp-hub'.
# You don't need to manually list them here.

# --- Script Body ---
try {
    # Get the directory where the script is located (your project root)
    $projectRoot = $PSScriptRoot
    if (-not $projectRoot) { $projectRoot = Get-Location }

    $srcPath = Join-Path -Path $projectRoot -ChildPath "src"
    $mcpHubPath = Join-Path -Path $srcPath -ChildPath "server\mcp-hub"
    $venvActivatePath = Join-Path -Path $srcPath -ChildPath "server\venv\Scripts\activate.ps1"

    # Verify that the necessary paths exist
    if (-not (Test-Path -Path $srcPath)) { throw "The 'src' directory was not found. Please run this script from the project root." }
    if (-not (Test-Path -Path $mcpHubPath)) { throw "The 'src/server/mcp-hub' directory was not found." }
    if (-not (Test-Path -Path $venvActivatePath)) { throw "The venv activation script was not found at '$venvActivatePath'." }

    # Find all MCP server directories
    $mcpServers = Get-ChildItem -Path $mcpHubPath -Directory | Select-Object -ExpandProperty Name

    if ($mcpServers.Count -eq 0) {
        throw "No MCP server directories found in '$mcpHubPath'."
    }

    Write-Host "Found the following MCP servers:" -ForegroundColor Green
    $mcpServers | ForEach-Object { Write-Host " - $_" }
    Write-Host ""

    # Loop through each server and launch it in a new terminal
    foreach ($serverName in $mcpServers) {
        $windowTitle = "MCP - $($serverName.ToUpper())"
        $pythonModule = "server.mcp-hub.$serverName.main"

        Write-Host "🚀 Launching $windowTitle..." -ForegroundColor Yellow

        # Define the sequence of commands to run in the new terminal
        $commandToRun = "& '$venvActivatePath'; python -m '$pythonModule'"

        # Use Start-Process to launch a new PowerShell window
        # -WorkingDirectory ensures all commands run from the correct path ('src').
        # -ArgumentList passes the commands to the new PowerShell instance.
        # -NoExit keeps the window open after the script finishes to see the output.
        $startProcessArgs = @{
            FilePath         = "powershell.exe"
            WorkingDirectory = $srcPath
            ArgumentList     = "-NoExit", "-Command", "Set-Location -Path '$srcPath'; `$Host.UI.RawUI.WindowTitle = '$windowTitle'; $commandToRun"
        }

        Start-Process @startProcessArgs

        # A short pause to prevent all windows from opening at the exact same time
        Start-Sleep -Milliseconds 300
    }

    Write-Host "`n✅ All MCP servers have been launched in new terminals." -ForegroundColor Green

}
catch {
    Write-Error "An error occurred: $_"
    # Pause to allow the user to read the error before the script exits
    Read-Host "Press Enter to exit..."
}