$configPath = ".\experiments\configs\live_demo.json"

Write-Host "Registering functions for Live Demo..."
.\venv\Scripts\python.exe .\backend\utils\register_functions.py $configPath "adaptive"

Write-Host "Starting continuous live traffic..."
while ($true) {
    .\venv\Scripts\python.exe .\workloads\runner.py $configPath
}
