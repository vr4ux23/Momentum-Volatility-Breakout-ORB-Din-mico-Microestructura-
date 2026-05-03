# 🚀 Guía de Despliegue — HFT Momentum Bot

> **Orquestador principal:** PM2 (Node.js)  
> **Backup de emergencia:** `start_vps.bat`

---

## Prerrequisitos

| Software | Versión | Verificación |
|----------|---------|-------------|
| Windows | 10/Server 2019+ | Permisos de **Administrador** |
| Python | 3.10+ (64-bit) | `python --version` |
| Node.js | 18+ LTS | `node --version` |
| PM2 | Latest | `npm install -g pm2` |
| MetaTrader 5 | Última | Terminal instalado en `C:\Users\vr4ux23\Documents\Estrategia con VWAP\` |
| PostgreSQL | 15+ | Servicio corriendo (`pg_isready`) |
| Git | 2.x | `git --version` |

> ⚠️ **Crítico:** MetaTrader 5 debe estar **abierto y con sesión activa** para que el bot se conecte vía IPC. La librería `MetaTrader5` de Python se comunica con el proceso `terminal64.exe`.

---

## Paso 1: Clonar el Repositorio

```powershell
# Abrir PowerShell como Administrador
git clone https://github.com/vr4ux23/Momentum-Volatility-Breakout-ORB-Din-mico-Microestructura-.git C:\TradingBot
Set-Location C:\TradingBot
```

---

## Paso 2: Crear Entorno Virtual

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

> ⚠️ Si PowerShell bloquea la activación del venv, ejecuta primero:
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```

Verificar que Python apunta al venv:

```powershell
Get-Command python | Select-Object Source
# Debe mostrar: C:\TradingBot\venv\Scripts\python.exe
```

---

## Paso 3: Instalar Dependencias

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Verificación de MetaTrader5:

```powershell
python -c "import MetaTrader5; print('MT5 version:', MetaTrader5.__version__)"
```

> ⚠️ Si `MetaTrader5` falla al importar:
> - Verificar que Python es **64-bit**: `python -c "import struct; print(struct.calcsize('P') * 8, 'bits')"`
> - Verificar que MetaTrader 5 terminal está instalado en el sistema

---

## Paso 4: Configurar Secretos

```powershell
Copy-Item .env.example .env
notepad .env
```

Editar `.env` con los valores reales:

```ini
# ============================
# MetaTrader 5
# ============================
MT5_LOGIN=TU_NUMERO_DE_CUENTA
MT5_PASSWORD=TU_PASSWORD_REAL
MT5_SERVER=TU_BROKER-Server
MT5_PATH=C:\Users\vr4ux23\Documents\Estrategia con VWAP\terminal64.exe

# ============================
# PostgreSQL
# ============================
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASS=TU_PASSWORD_DB_REAL
DB_NAME=hft

# ============================
# Entorno
# ============================
ENV_MODE=PROD
```

> 🔒 **NUNCA** subas `.env` a Git. Ya está en `.gitignore`.

---

## Paso 5: Configurar Base de Datos

### Opción A: Script automático (CMD)

```powershell
cmd /c "scripts\setup_db.bat"
```

### Opción B: Manual con PowerShell

```powershell
# Crear la base de datos (si no existe)
& psql -U postgres -c "SELECT 1 FROM pg_database WHERE datname = 'hft'" | Out-Null
if ($LASTEXITCODE -ne 0) {
    & psql -U postgres -c "CREATE DATABASE hft;"
}

# Crear tablas e índices
& psql -U postgres -d hft -f scripts\setup_db.sql
```

### Opción C: Una línea directa

```powershell
psql -U postgres -c "CREATE DATABASE hft;" 2>$null; psql -U postgres -d hft -f scripts\setup_db.sql
```

---

## Paso 6: Entrenar Modelo ML

Con MetaTrader 5 **abierto y conectado** al broker:

```powershell
python scripts\train_model.py
```

Esto descargará 3000 barras H1 de EURUSD, entrenará un RandomForest y guardará el modelo en `models\rf_classifier_v1.pkl`.

Verificar:

```powershell
Test-Path models\rf_classifier_v1.pkl
# Debe retornar: True
```

---

## Paso 7: Health Check

```powershell
python scripts\health_check.py
```

Verifica automáticamente:
- ✅ Python >= 3.10
- ✅ Ejecutando dentro del venv
- ✅ Todas las librerías instaladas (incluyendo el binario `.pyd` de MT5)
- ✅ `.env` con variables reales (no placeholders)
- ✅ Modelo ML presente
- ✅ Conexión a PostgreSQL + tablas `trade_logs` y `microstructure_logs`

---

## Paso 8: Arrancar con PM2

### 8.1 Instalar PM2 (si no está)

```powershell
npm install -g pm2
pm2 --version
```

### 8.2 Arrancar el bot

```powershell
Set-Location C:\TradingBot
pm2 start ecosystem.config.js --merge-logs
pm2 save
```

### 8.3 Verificar que está corriendo

```powershell
pm2 status
pm2 logs HFT_Momentum_Bot --lines 50
```

### 8.4 Comandos útiles de PM2

```powershell
# Ver logs en tiempo real
pm2 logs HFT_Momentum_Bot

# Reiniciar el bot
pm2 restart HFT_Momentum_Bot

# Detener el bot
pm2 stop HFT_Momentum_Bot

# Ver métricas (CPU, RAM, uptime)
pm2 monit

# Configurar PM2 para arrancar con Windows
pm2 startup
pm2 save
```

### 8.5 Arranque de emergencia (sin PM2)

Si PM2 no está disponible, usar el batch de respaldo:

```powershell
cmd /c start_vps.bat
```

---

## Estructura Final

```
C:\TradingBot\
├── .env                    ← Tus secretos (NO en Git)
├── .env.example
├── .gitignore
├── DEPLOY.md               ← Este archivo
├── config\
│   └── config.yaml
├── core\
│   ├── mt5_connection.py   ← Lee MT5_PATH de .env
│   └── scheduler.py
├── data\
│   ├── pg_logger.py        ← Lee DB_* de .env
│   ├── pre_open_buffer.py
│   └── tick_listener.py
├── ecosystem.config.js     ← PM2: interpreter → venv python
├── execution\
│   ├── order_manager.py
│   └── position_manager.py
├── main.py                 ← Lee DB config de .env (no hardcoded)
├── ml\
│   └── ml_filter.py
├── models\
│   └── rf_classifier_v1.pkl  ← Generado por train_model.py
├── requirements.txt        ← Versiones pinneadas
├── risk\
│   └── compliance_layer.py
├── scripts\
│   ├── health_check.py     ← Diagnóstico de entorno
│   ├── setup_db.bat
│   ├── setup_db.sql        ← DDL con IF NOT EXISTS
│   └── train_model.py
├── start_vps.bat           ← Backup de emergencia
└── venv\                   ← Entorno virtual (NO en Git)
```

---

## Troubleshooting

| Problema | Comando de Diagnóstico | Solución |
|----------|----------------------|----------|
| `ModuleNotFoundError: MetaTrader5` | `pip show MetaTrader5` | Verificar Python 64-bit. `pip install MetaTrader5` |
| `mt5.initialize() retorna False` | `python -c "import MetaTrader5 as mt5; mt5.initialize(); print(mt5.last_error())"` | Abrir MetaTrader 5 terminal manualmente primero |
| `psycopg2 connection refused` | `pg_isready -h localhost -p 5432` | Verificar servicio PostgreSQL: `Get-Service postgresql*` |
| `Modelo no encontrado` | `Test-Path models\rf_classifier_v1.pkl` | `python scripts\train_model.py` |
| `.env not found` | `Test-Path .env` | `Copy-Item .env.example .env` |
| PM2 no arranca | `pm2 logs --err` | Revisar rutas en `ecosystem.config.js` |
| PowerShell bloquea scripts | `Get-ExecutionPolicy` | `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser` |
| MT5 abre terminal equivocado | Verificar `MT5_PATH` en `.env` | Debe ser ruta exacta a `terminal64.exe` de tu broker |
