$env:PYTHONPATH = $PWD.Path
$Timeouts = @(30, 60, 300, 600)
$config = "burst_001"

New-Item -ItemType Directory -Force -Path ".\experiments\results" | Out-Null

foreach ($timeout in $Timeouts) {
    Write-Host "Running idle timeout $timeout with $config..."
    
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
    Start-Sleep -Seconds 3
    
    # Register Hello
    $payload_hello = @{
        name = "hello"
        image = "lambdax-hello:latest"
        max_containers = 5
        idle_timeout_seconds = $timeout
        scheduling_policy = "reactive"
        min_containers = 0
        queue_threshold = 0
    }
    Invoke-RestMethod -Uri "http://127.0.0.1:8000/functions/register" -Method Post -Body ($payload_hello | ConvertTo-Json) -ContentType "application/json" | Out-Null
    
    # Run workload
    .\venv\Scripts\python.exe .\workloads\runner.py ".\experiments\configs\$config.json"
    
    # Wait for the timeout to pass + 5 seconds to observe reaping
    Write-Host "Waiting for $timeout seconds to observe idle timeout reaping..."
    Start-Sleep -Seconds ($timeout + 5)
    
    # Generate Report
    $report_file = ".\experiments\results\phase4_timeout_${timeout}.txt"
    .\venv\Scripts\python.exe .\workloads\reporter.py > $report_file
    
    # Stop Server
    Stop-Job -Job $job
    Remove-Job -Job $job -Force
    Start-Sleep -Seconds 2
}
Write-Host "Idle Timeout Experiments Completed!"
