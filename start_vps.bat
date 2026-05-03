@echo off
cd /d "%~dp0"

if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

where pm2 >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    pm2 start ecosystem.config.js --merge-logs
    pm2 save
) else (
    python main.py
)
