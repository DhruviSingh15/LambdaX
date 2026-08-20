$env:PYTHONPATH = $PWD.Path
$configPath = "backend/scheduler/adaptive/config.json"
$backupPath = "backend/scheduler/adaptive/config.backup.json"

Copy-Item $configPath $backupPath -Force -ErrorAction SilentlyContinue

$py_script = @"
import json
with open('$configPath', 'r') as f:
    d = json.load(f)
d['enable_priority'] = True
d['enable_micro_queue'] = True
d['enable_cost_model'] = True
d['enable_predictive_reclaim'] = True
with open('$configPath', 'w') as f:
    json.dump(d, f, indent=4)
"@
$py_script | Out-File "update_config.py" -Encoding utf8
.\venv\Scripts\python.exe update_config.py

Write-Host "Running Priority Contention Experiment..."

# Clean state
Remove-Item -Path "lambdax.db" -Force -ErrorAction SilentlyContinue
docker rm -f (docker ps -aq) 2>$null

# Start server
$job = Start-Job -ScriptBlock {
    param($path)
    Set-Location $path
    $env:PYTHONPATH = $path
    .\venv\Scripts\python.exe -m uvicorn backend.main:app --port 8000
} -ArgumentList $PWD.Path

# Wait for server
$server_up = $false
for ($i = 0; $i -lt 15; $i++) {
    $tcpCheck = Test-NetConnection -ComputerName 127.0.0.1 -Port 8000 -InformationLevel Quiet -WarningAction SilentlyContinue
    if ($tcpCheck -eq $true) {
        $server_up = $true
        break
    }
    Start-Sleep -Seconds 1
}

if (-not $server_up) {
    Write-Host "Server failed to start!"
    exit 1
}

# Register high priority
$payload_high = @{
    name = "high_pri"
    image = "lambdax-hello:latest"
    max_containers = 10
    idle_timeout_seconds = 10
    scheduling_policy = "adaptive"
    min_containers = 0
    sla_ms = 200
}
Invoke-RestMethod -Uri "http://127.0.0.1:8000/functions/register" -Method Post -Body ($payload_high | ConvertTo-Json) -ContentType "application/json" | Out-Null

# Register low priority
$payload_low = @{
    name = "low_pri"
    image = "lambdax-hello:latest"
    max_containers = 10
    idle_timeout_seconds = 10
    scheduling_policy = "adaptive"
    min_containers = 0
    sla_ms = 2000
}
Invoke-RestMethod -Uri "http://127.0.0.1:8000/functions/register" -Method Post -Body ($payload_low | ConvertTo-Json) -ContentType "application/json" | Out-Null

# Run workload
Write-Host "Starting workload..."
.\venv\Scripts\python.exe .\workloads\runner.py ".\experiments\configs\contention_001.json"

# Generate Report
$report_file = ".\experiments\results\phase7\contention_priority.txt"
.\venv\Scripts\python.exe .\workloads\reporter.py > $report_file

# Stop Server
Stop-Job -Job $job
Remove-Job -Job $job -Force
Start-Sleep -Seconds 3

Copy-Item $backupPath $configPath -Force
Remove-Item "update_config.py" -Force
Write-Host "Priority Contention Experiment Completed!"
