@echo off
REM ============================================
REM  HFT Momentum Bot - Arranque de Produccion
REM ============================================
cd /d "%~dp0"

echo [%date% %time%] Iniciando bot HFT...

REM --- Verificar venv ---
if not exist "venv\Scripts\activate.bat" (
    echo [ERROR] No se encontro venv\Scripts\activate.bat
    echo         Ejecuta: python -m venv venv
    pause
    exit /b 1
)
call venv\Scripts\activate.bat

REM --- Verificar Python del venv ---
python --version >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python no disponible en el venv.
    pause
    exit /b 1
)

REM --- Verificar .env ---
if not exist ".env" (
    echo [ERROR] Archivo .env no encontrado.
    echo         Ejecuta: copy .env.example .env  y completa los valores.
    pause
    exit /b 1
)

REM --- Arrancar con PM2 o directo ---
where pm2 >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    echo [INFO] Usando PM2 como supervisor...
    pm2 start ecosystem.config.js --merge-logs
    pm2 save
) else (
    echo [INFO] PM2 no encontrado. Ejecutando main.py directamente...
    python main.py
)
