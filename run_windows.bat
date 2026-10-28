@echo off
cd /d "%~dp0"
python car_service.py
if errorlevel 1 py car_service.py
pause
