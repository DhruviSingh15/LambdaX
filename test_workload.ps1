$env:PYTHONPATH = $PWD.Path
Remove-Item -Path "lambdax.db" -Force -ErrorAction SilentlyContinue

# Build compute image
docker build -t lambdax-compute:latest .\functions\compute\

# Start FastAPI server in background
$ServerProcess = Start-Process -FilePath ".\venv\Scripts\python.exe" -ArgumentList "-m uvicorn backend.main:app --port 8000" -PassThru -NoNewWindow
Start-Sleep -Seconds 3

# Register Hello
$payload_hello = @{
    name = "hello"
    image = "lambdax-hello:latest"
    max_containers = 5
    idle_timeout_seconds = 300
}
Invoke-RestMethod -Uri "http://127.0.0.1:8000/functions/register" -Method Post -Body ($payload_hello | ConvertTo-Json) -ContentType "application/json" | Out-Null

# Register Compute
$payload_compute = @{
    name = "compute"
    image = "lambdax-compute:latest"
    max_containers = 3
    idle_timeout_seconds = 300
}
Invoke-RestMethod -Uri "http://127.0.0.1:8000/functions/register" -Method Post -Body ($payload_compute | ConvertTo-Json) -ContentType "application/json" | Out-Null

# Run workload
.\venv\Scripts\python.exe .\workloads\runner.py .\experiments\configs\mixed_001.json

# Run reporter
.\venv\Scripts\python.exe .\workloads\reporter.py

Stop-Process -InputObject $ServerProcess -Force
