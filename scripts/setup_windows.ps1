# One-time setup on Windows. Run from the repo root:  powershell -ExecutionPolicy Bypass -File scripts\setup_windows.ps1
python -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\pip install -e .
.\.venv\Scripts\python -m playwright install chromium
.\.venv\Scripts\python -m metalscout init
.\.venv\Scripts\python -m metalscout schedule install
Write-Host "Done. Edit metalscout.yaml, then double-click scripts\start_dashboard.bat"
