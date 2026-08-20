$env:PYTHONPATH = $PWD.Path
$policies = @("reactive", "predictive", "adaptive")
$configPath = "backend/scheduler/adaptive/config.json"
$backupPath = "backend/scheduler/adaptive/config.backup.json"

Copy-Item $configPath $backupPath -Force -ErrorAction SilentlyContinue

# Ensure Adaptive runs with full features
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

New-Item -ItemType Directory -Force -Path ".\experiments\results\phase7" | Out-Null

foreach ($policy in $policies) {
    Write-Host "Running Full Matrix Config: $policy"
    
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
        break
    }
    
    # Register hello
    $payload_hello = @{
        name = "hello"
        image = "lambdax-hello:latest"
        max_containers = 10
        idle_timeout_seconds = 10
        scheduling_policy = $policy
        min_containers = 0
    }
    Invoke-RestMethod -Uri "http://127.0.0.1:8000/functions/register" -Method Post -Body ($payload_hello | ConvertTo-Json) -ContentType "application/json" | Out-Null
    
    # Register compute
    $payload_compute = @{
        name = "compute"
        image = "lambdax-hello:latest" # reuse image for simplicity
        max_containers = 10
        idle_timeout_seconds = 10
        scheduling_policy = $policy
        min_containers = 0
    }
    Invoke-RestMethod -Uri "http://127.0.0.1:8000/functions/register" -Method Post -Body ($payload_compute | ConvertTo-Json) -ContentType "application/json" | Out-Null
    
    # Run workload
    Write-Host "Starting workload for $policy..."
    .\venv\Scripts\python.exe .\workloads\runner.py ".\experiments\configs\mixed_001.json"
    
    # Generate Report
    $report_file = ".\experiments\results\phase7\matrix_$($policy).txt"
    .\venv\Scripts\python.exe .\workloads\reporter.py > $report_file
    
    # Stop Server
    Stop-Job -Job $job
    Remove-Job -Job $job -Force
    Start-Sleep -Seconds 3
}

Copy-Item $backupPath $configPath -Force
Remove-Item "update_config.py" -Force
Write-Host "Full Matrix Experiments Completed!"
