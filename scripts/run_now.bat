@echo off
REM Run one full lead search now (no dashboard needed). Results: exports\leads_latest.xlsx
cd /d "%~dp0.."
if exist .venv\Scriptsctivate.bat call .venv\Scriptsctivate.bat
python -m metalscout run
pause
