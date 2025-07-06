# PowerShell script to start Redis inside WSL and test connection

Write-Host "▶️ Starting Redis server in WSL..."
wsl sudo service redis-server start

Write-Host "🔄 Testing Redis connection with redis-cli ping..."
$pingResult = wsl redis-cli ping

if ($pingResult -eq "PONG") {
    Write-Host "✅ Redis is running and responding correctly: $pingResult"
} else {
    Write-Host "❌ Redis did not respond correctly. Output: $pingResult"
}