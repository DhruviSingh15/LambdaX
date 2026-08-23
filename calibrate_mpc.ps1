$workloads = @("bursty_001", "periodic_001", "mixed_001")
$seed = 999 # Calibration seed

$out_dir = ".\experiments\results\phase9_calibration"
$raw_dir = "$out_dir\raw"
$csv_path = "$out_dir\calibration_results.csv"

New-Item -ItemType Directory -Force -Path $out_dir | Out-Null
New-Item -ItemType Directory -Force -Path $raw_dir | Out-Null

"experiment_id,policy,workload,seed,repetition,function,sla_compliance,cold_start_rate,p50_latency,p95_latency,p99_latency,p95_queue,container_seconds,invocation_count" | Out-File $csv_path -Encoding utf8

$configs = @(
    # Set A
    '{"horizon": 4, "step_seconds": 5, "cost_weight": 1.0, "latency_weight": 1.0, "sla_weight": 2.0, "queue_weight": 1.0, "max_start_rate": 5, "max_prewarm_per_step": 3}',
    # Set B
    '{"horizon": 4, "step_seconds": 5, "cost_weight": 2.0, "latency_weight": 1.0, "sla_weight": 3.0, "queue_weight": 2.0, "max_start_rate": 5, "max_prewarm_per_step": 3}',
    # Set C
    '{"horizon": 4, "step_seconds": 5, "cost_weight": 1.0, "latency_weight": 2.0, "sla_weight": 4.0, "queue_weight": 2.0, "max_start_rate": 5, "max_prewarm_per_step": 3}'
)
$config_names = @("SetA", "SetB", "SetC")

for ($c = 0; $c -lt 3; $c++) {
    $conf_json = $configs[$c]
    $conf_name = $config_names[$c]
    
    $conf_json | Out-File ".\mpc_config.json" -Encoding utf8
    Write-Host "Evaluating MPC Calibration: $conf_name"
    
    foreach ($wl in $workloads) {
        $configPath = ".\experiments\configs\$wl.json"
        $exp_id = "mpc_${conf_name}_${wl}_${seed}"
        $run_dir = "$raw_dir\run_$exp_id"
        New-Item -ItemType Directory -Force -Path $run_dir | Out-Null

        # Clean
        Remove-Item -Path "lambdax.db" -Force -ErrorAction SilentlyContinue
        docker rm -f (docker ps -aq) 2>$null

        $job = Start-Job -ScriptBlock {
            param($path)
            Set-Location $path
            $env:PYTHONPATH = $path
            .\venv\Scripts\python.exe -m uvicorn backend.main:app --port 8000
        } -ArgumentList $PWD.Path
        
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
        
        .\venv\Scripts\python.exe .\backend\utils\register_functions.py $configPath "mpc"
        .\venv\Scripts\python.exe .\workloads\runner.py $configPath --seed $seed
        $valid = .\venv\Scripts\python.exe .\backend\utils\validate_run.py lambdax.db $configPath
        
        if ($LASTEXITCODE -eq 0) {
            .\venv\Scripts\python.exe .\workloads\reporter_csv.py $exp_id "mpc_$conf_name" $wl $seed 1 | Out-File $csv_path -Append -Encoding utf8
        }
        
        Stop-Job -Job $job
        Remove-Job -Job $job -Force
        Start-Sleep -Seconds 3
    }
}
Write-Host "Calibration Complete!"
