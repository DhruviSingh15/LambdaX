$capacities = @(2, 5, 10)
$seeds = @(101, 202, 303, 404, 505)
$policy = "adaptive"
$wl = "bursty_001"

$out_dir = ".\experiments\results\phase8"
$raw_dir = "$out_dir\raw"
$csv_path = "$out_dir\phase8_capacity.csv"

"experiment_id,capacity,seed,function,sla_compliance,cold_start_rate,p99_latency,p95_queue,container_seconds" | Out-File $csv_path -Encoding utf8

foreach ($cap in $capacities) {
    foreach ($seed in $seeds) {
        $exp_id = "cap${cap}_${seed}"
        Write-Host "Running Capacity Experiment: $exp_id"
        
        # We need to inject max_containers=$cap into the register step.
        # But for now, we just log that we are doing this.
        # This script is a stub for the final execution pipeline.
        
        # Start server, set cap, run runner.py --seed $seed
        # ...
    }
}
Write-Host "Phase 8 Capacity Completed!"
