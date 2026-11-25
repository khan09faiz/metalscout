@echo off
REM Double-click to open the MetalScout dashboard (also runs the daily schedule while open).
cd /d "%~dp0.."
if exist .venv\Scriptsctivate.bat call .venv\Scriptsctivate.bat
start "" http://localhost:8000
python -m metalscout serve
