Write-Host "Starting Phase 8 Validation Suite"

Write-Host "1. Running Core Matrix..."
.\run_phase8_matrix.ps1

Write-Host "2. Running Capacity Tests..."
.\run_phase8_capacity.ps1

Write-Host "3. Running Fault Injection Tests..."
.\run_phase8_faults.ps1

Write-Host "4. Generating Statistics and Pareto Plots..."
.\venv\Scripts\python.exe .\analyze_phase8.py ".\experiments\results\phase8\phase8_raw_results.csv" ".\experiments\results\phase8"

Write-Host "Phase 8 Evaluation Pipeline Complete!"
