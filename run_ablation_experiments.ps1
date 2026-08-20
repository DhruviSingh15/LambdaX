$env:PYTHONPATH = $PWD.Path
$config_path = "backend/scheduler/adaptive/config.json"
$backup_path = "backend/scheduler/adaptive/config.backup.json"

Copy-Item $config_path $backup_path -Force -ErrorAction SilentlyContinue

$ablations = @(
    @{ Name = "A_Full_Adaptive"; Priority = "True"; MicroQueue = "True"; Cost = "True"; Reclaim = "True" },
    @{ Name = "B_No_Priority"; Priority = "False"; MicroQueue = "True"; Cost = "True"; Reclaim = "True" },
    @{ Name = "C_No_MicroQueue"; Priority = "True"; MicroQueue = "False"; Cost = "True"; Reclaim = "True" },
    @{ Name = "D_No_Cost"; Priority = "True"; MicroQueue = "True"; Cost = "False"; Reclaim = "True" },
    @{ Name = "E_No_Reclaim"; Priority = "True"; MicroQueue = "True"; Cost = "True"; Reclaim = "False" }
)

New-Item -ItemType Directory -Force -Path ".\experiments\results\phase7" | Out-Null

foreach ($ablation in $ablations) {
    Write-Host "Running Ablation Config: $($ablation.Name)"
    
    # Update config.json using python to ensure valid json
    $py_script = @"
import json
with open('$config_path', 'r') as f:
    d = json.load(f)
d['enable_priority'] = $($ablation.Priority)
d['enable_micro_queue'] = $($ablation.MicroQueue)
d['enable_cost_model'] = $($ablation.Cost)
d['enable_predictive_reclaim'] = $($ablation.Reclaim)
with open('$config_path', 'w') as f:
    json.dump(d, f, indent=4)
"@
    $py_script | Out-File "update_config.py" -Encoding utf8
    .\venv\Scripts\python.exe update_config.py
    
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
    
    # Register function
    $payload = @{
        name = "hello"
        image = "lambdax-hello:latest"
        max_containers = 10
        idle_timeout_seconds = 10
        scheduling_policy = "adaptive"
        min_containers = 0
    }
    Invoke-RestMethod -Uri "http://127.0.0.1:8000/functions/register" -Method Post -Body ($payload | ConvertTo-Json) -ContentType "application/json" | Out-Null
    
    # Run workload
    Write-Host "Starting workload for $($ablation.Name)..."
    .\venv\Scripts\python.exe .\workloads\runner.py ".\experiments\configs\mixed_001.json"
    
    # Generate Report
    $report_file = ".\experiments\results\phase7\ablation_$($ablation.Name).txt"
    .\venv\Scripts\python.exe .\workloads\reporter.py > $report_file
    
    # Stop Server
    Stop-Job -Job $job
    Remove-Job -Job $job -Force
    
    # Wait for processes to exit
    Start-Sleep -Seconds 3
}

# Restore config
Copy-Item $backup_path $config_path -Force
Remove-Item "update_config.py" -Force
Write-Host "Ablation Experiments Completed!"
