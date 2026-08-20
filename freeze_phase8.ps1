$phase8_dir = ".\experiments\results\phase8"
New-Item -ItemType Directory -Force -Path "$phase8_dir\raw" | Out-Null
New-Item -ItemType Directory -Force -Path "$phase8_dir\figures" | Out-Null

$git_hash = git rev-parse HEAD
$python_version = (python --version)
$docker_version = (docker --version)
$timestamp = (Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ")
$cpu = (Get-WmiObject Win32_Processor | Select-Object -ExpandProperty Name)
$ram = (Get-WmiObject Win32_ComputerSystem | Select-Object -ExpandProperty TotalPhysicalMemory)

pip freeze > "$phase8_dir\requirements-lock.txt"
"Git Hash: $git_hash" | Out-File "$phase8_dir\CODE_VERSION.txt" -Encoding utf8
"Python: $python_version" | Out-File "$phase8_dir\CODE_VERSION.txt" -Append -Encoding utf8
"Docker: $docker_version" | Out-File "$phase8_dir\CODE_VERSION.txt" -Append -Encoding utf8
"Timestamp: $timestamp" | Out-File "$phase8_dir\CODE_VERSION.txt" -Append -Encoding utf8

$manifest = @{
    git_hash = $git_hash
    python_version = $python_version
    docker_version = $docker_version
    cpu = $cpu
    ram_bytes = $ram
    timestamp = $timestamp
    seeds = @(101, 202, 303, 404, 505)
    workloads = @("constant_001", "bursty_001", "periodic_001", "poisson_001", "mixed_001")
    policies = @("reactive", "fixed", "threshold", "predictive_ema", "predictive_hybrid", "adaptive")
}

$manifest | ConvertTo-Json -Depth 5 | Out-File "$phase8_dir\experiment_manifest.json" -Encoding utf8
Write-Host "Frozen Phase 8 Code and generated manifests."
