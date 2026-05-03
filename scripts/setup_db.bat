@echo off
REM ============================================
REM  Setup PostgreSQL Database
REM  Auto-detecta psql.exe en rutas comunes
REM ============================================
cd /d "%~dp0\.."

if not exist ".env" (
    echo [ERROR] .env no encontrado. Copia .env.example a .env primero.
    pause
    exit /b 1
)

REM --- Leer variables de .env ---
for /f "usebackq tokens=1,* delims==" %%a in (".env") do (
    set "%%a=%%b"
)

REM --- Auto-detectar psql.exe ---
set "PSQL_EXE="

REM Intentar psql en PATH primero
where psql >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    set "PSQL_EXE=psql"
    goto :psql_found
)

REM Buscar en rutas por defecto de PostgreSQL 17, 16, 15, 14
for %%V in (17 16 15 14) do (
    if exist "C:\Program Files\PostgreSQL\%%V\bin\psql.exe" (
        set "PSQL_EXE=C:\Program Files\PostgreSQL\%%V\bin\psql.exe"
        goto :psql_found
    )
)

REM No se encontro automaticamente — pedir al usuario
echo.
echo [AVISO] No se encontro psql.exe en las rutas por defecto:
echo         - PATH del sistema
echo         - C:\Program Files\PostgreSQL\{17,16,15,14}\bin\
echo.
set /p "PSQL_EXE=Ingresa la ruta completa a psql.exe: "

if not exist "%PSQL_EXE%" (
    echo [ERROR] Ruta no valida: %PSQL_EXE%
    echo         Verifica la instalacion de PostgreSQL.
    pause
    exit /b 1
)

:psql_found
echo [INFO] Usando psql: %PSQL_EXE%
echo [INFO] Base de datos: %DB_NAME%
echo [INFO] Host: %DB_HOST%:%DB_PORT%  User: %DB_USER%
echo.

REM --- Crear base de datos si no existe ---
echo [INFO] Verificando base de datos...
"%PSQL_EXE%" -h %DB_HOST% -p %DB_PORT% -U %DB_USER% -tc "SELECT 1 FROM pg_database WHERE datname='%DB_NAME%'" | findstr "1" >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [INFO] Creando base de datos '%DB_NAME%'...
    "%PSQL_EXE%" -h %DB_HOST% -p %DB_PORT% -U %DB_USER% -c "CREATE DATABASE %DB_NAME%;"
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] No se pudo crear la base de datos.
        pause
        exit /b 1
    )
    echo [OK] Base de datos creada.
) else (
    echo [OK] Base de datos '%DB_NAME%' ya existe.
)

REM --- Crear tablas ---
echo [INFO] Ejecutando setup_db.sql...
"%PSQL_EXE%" -h %DB_HOST% -p %DB_PORT% -U %DB_USER% -d %DB_NAME% -f scripts\setup_db.sql

if %ERRORLEVEL% EQU 0 (
    echo.
    echo [OK] Tablas e indices creados exitosamente.
) else (
    echo.
    echo [ERROR] Fallo al crear tablas. Verifica credenciales y que PostgreSQL este corriendo.
)
pause
