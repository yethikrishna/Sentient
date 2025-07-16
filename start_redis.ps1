# --- CONFIGURATION ---
# Path to your .env file
$envFilePath = Join-Path $PSScriptRoot "src\server\.env"

# Default WSL distro name
$wslDistroName = "Ubuntu"

# --- FUNCTIONS ---

# Helper: Extract REDIS_PASSWORD from .env
function Get-RedisPassword {
    param([string]$envPath)
    if (-not (Test-Path $envPath)) {
        throw "❌ Could not find .env file at: $envPath"
    }

    $envContent = Get-Content $envPath
    $passwordLine = $envContent | Select-String -Pattern "^\s*REDIS_PASSWORD\s*=\s*['""]?(.*?)['""]?\s*$"
    if ($passwordLine) {
        return $passwordLine.Matches[0].Groups[1].Value.Trim()
    }
    else {
        throw "❌ Could not find REDIS_PASSWORD in $envPath"
    }
}

# Helper: Check if Redis is installed in WSL
function Check-RedisInstalled {
    param([string]$distro)
    Write-Host "🔍 Checking if Redis is installed in WSL ($distro)..."
    $checkCommand = "which redis-server"
    $checkResult = wsl -d $distro --% bash -c "$checkCommand"

    if (-not $checkResult) {
        throw "❌ Redis server is not installed in WSL ($distro). Please install it using: sudo apt install redis-server"
    }
    else {
        Write-Host "✅ Redis is installed at: $checkResult" -ForegroundColor Green
    }
}

# Helper: Start Redis server in WSL
function Start-RedisServer {
    param([string]$distro, [string]$password)
    Write-Host "▶️ Starting Redis server in WSL ($distro)..."
    $startCommand = "redis-server --bind 0.0.0.0 --requirepass `"$password`""
    wsl -d $distro --% bash -c "$startCommand"
    Start-Sleep -Seconds 2
}

# Helper: Test Redis connectivity
function Test-RedisConnection {
    param([string]$distro, [string]$password)
    Write-Host "🔄 Testing Redis connection with redis-cli PING..."
    $pingCommand = "redis-cli -a `"$password`" PING"
    $pingResult = wsl -d $distro --% bash -c "$pingCommand"

    if ($pingResult -eq "PONG") {
        Write-Host "✅ Redis is running and responding correctly: $pingResult" -ForegroundColor Green
    }
    else {
        Write-Host "❌ Redis did not respond correctly. Output: $pingResult" -ForegroundColor Red
        throw "Failed to authenticate with Redis. Check your REDIS_PASSWORD and Redis configuration."
    }
}

# --- MAIN LOGIC ---
try {
    # Get Redis password from .env
    $redisPassword = Get-RedisPassword -envPath $envFilePath

    # Check if Redis is installed in WSL
    Check-RedisInstalled -distro $wslDistroName

    # Start Redis in WSL
    Start-RedisServer -distro $wslDistroName -password $redisPassword

    # Test connection
    Test-RedisConnection -distro $wslDistroName -password $redisPassword
}
catch {
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}