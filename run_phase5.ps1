$env:PYTHONPATH = $PWD.Path
$Configs = @("constant_001", "burst_001", "periodic_001", "poisson_001", "mixed_001")
$Policies = @("reactive", "fixed", "threshold", "predictive_naive", "predictive_ma", "predictive_ema")

New-Item -ItemType Directory -Force -Path ".\experiments\results\phase5" | Out-Null

foreach ($policy in $Policies) {
    foreach ($config in $Configs) {
        Write-Host "Running $policy with $config..."
        
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
        
        # Determine policy parameters
        $min_containers = if ($policy -eq "fixed") { 3 } else { 0 }
        $queue_threshold = if ($policy -eq "threshold") { 2 } else { 0 }
        
        # Register Hello
        $payload_hello = @{
            name = "hello"
            image = "lambdax-hello:latest"
            max_containers = 5
            idle_timeout_seconds = 300
            scheduling_policy = $policy
            min_containers = $min_containers
            queue_threshold = $queue_threshold
        }
        Invoke-RestMethod -Uri "http://127.0.0.1:8000/functions/register" -Method Post -Body ($payload_hello | ConvertTo-Json) -ContentType "application/json" | Out-Null
        
        # Register Compute
        $payload_compute = @{
            name = "compute"
            image = "lambdax-compute:latest"
            max_containers = 3
            idle_timeout_seconds = 300
            scheduling_policy = $policy
            min_containers = if ($policy -eq "fixed") { 2 } else { 0 }
            queue_threshold = $queue_threshold
        }
        Invoke-RestMethod -Uri "http://127.0.0.1:8000/functions/register" -Method Post -Body ($payload_compute | ConvertTo-Json) -ContentType "application/json" | Out-Null

        # Pre-warm delay
        Start-Sleep -Seconds 2

        # Run workload
        .\venv\Scripts\python.exe .\workloads\runner.py ".\experiments\configs\$config.json"
        
        # Run Leak & Over-provisioning Check
        $check_file = ".\experiments\results\phase5\${policy}_${config}_health.txt"
        .\venv\Scripts\python.exe .\tests\check_leaks.py > $check_file
        
        # Generate Report
        $report_file = ".\experiments\results\phase5\${policy}_${config}_report.txt"
        .\venv\Scripts\python.exe .\workloads\reporter.py > $report_file
        
        # Stop Server
        Stop-Job -Job $job
        Remove-Job -Job $job -Force
        Start-Sleep -Seconds 2
    }
}
Write-Host "Phase 5 Live Predictive Benchmarks Completed!"
