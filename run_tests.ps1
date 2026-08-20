$env:PYTHONPATH = $PWD.Path
Start-Process -FilePath ".\venv\Scripts\python.exe" -ArgumentList "-m uvicorn backend.main:app --host 127.0.0.1 --port 8000" -PassThru -NoNewWindow | Set-Variable -Name ServerProcess
Start-Sleep -Seconds 3
.\venv\Scripts\python.exe .\tests\test_phase2.py
$testExitCode = $LASTEXITCODE
Stop-Process -InputObject $ServerProcess -Force
exit $testExitCode
