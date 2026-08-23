$policies = @("reactive", "predictive_ema", "predictive_hybrid", "mpc", "adaptive")
$workloads = @("burst_001", "periodic_001", "mixed_001")
$seeds = @(101, 202, 303, 404, 505)

$out_dir = ".\experiments\results\phase9"
$raw_dir = "$out_dir\raw"
$csv_path = "$out_dir\phase9_raw_results.csv"

New-Item -ItemType Directory -Force -Path $out_dir | Out-Null
New-Item -ItemType Directory -Force -Path $raw_dir | Out-Null

# Write CSV header
"experiment_id,policy,workload,seed,repetition,function,sla_compliance,cold_start_rate,p50_latency,p95_latency,p99_latency,p95_queue,container_seconds,invocation_count" | Out-File $csv_path -Encoding utf8

$rep = 1
foreach ($seed in $seeds) {
    foreach ($wl in $workloads) {
        foreach ($policy in $policies) {
            $configPath = ".\experiments\configs\$wl.json"
            $exp_id = "${policy}_${wl}_${seed}"
            $run_dir = "$raw_dir\run_$exp_id"
            New-Item -ItemType Directory -Force -Path $run_dir | Out-Null

            Write-Host "Running: $exp_id"

            # Clean
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
                Stop-Job -Job $job
                Remove-Job -Job $job -Force
                continue
            }
            
            # Register functions
            .\venv\Scripts\python.exe .\backend\utils\register_functions.py $configPath $policy

            # Run workload
            .\venv\Scripts\python.exe .\workloads\runner.py $configPath --seed $seed

            # Validate
            $valid = .\venv\Scripts\python.exe .\backend\utils\validate_run.py lambdax.db $configPath
            if ($LASTEXITCODE -eq 0) {
                Write-Host "Run $exp_id VALID"
                # Generate stats and append to CSV
                .\venv\Scripts\python.exe .\workloads\reporter_csv.py $exp_id $policy $wl $seed $rep | Out-File $csv_path -Append -Encoding utf8
            } else {
                Write-Host "Run $exp_id INVALID - Skipping aggregation"
                "INVALID: $valid" | Out-File "$run_dir\invalid.log" -Encoding utf8
            }

            # Stop server
            Stop-Job -Job $job
            Remove-Job -Job $job -Force
            Start-Sleep -Seconds 3
        }
    }
    $rep++
}

Write-Host "Phase 9 Matrix Completed!"
