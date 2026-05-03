"""
HFT Momentum Bot - Health Check
Diagnostico rapido del entorno de produccion.
Ejecutar: python scripts/health_check.py
"""
import sys
import os
import importlib

# ============================================
# Constantes
# ============================================
REQUIRED_PYTHON = (3, 10)
REQUIRED_PACKAGES = [
    "MetaTrader5",
    "pandas",
    "numpy",
    "sklearn",
    "joblib",
    "psycopg2",
    "sqlalchemy",
    "yaml",
    "dotenv",
    "pytz",
]
REQUIRED_ENV_VARS = [
    "MT5_LOGIN",
    "MT5_PASSWORD",
    "MT5_SERVER",
    "DB_HOST",
    "DB_PORT",
    "DB_USER",
    "DB_PASS",
    "DB_NAME",
]

OK = "\u2705"
FAIL = "\u274c"
WARN = "\u26a0\ufe0f"
results = {"pass": 0, "fail": 0, "warn": 0}


def check(label, passed, msg_fail="", warn=False):
    if passed:
        print(f"  {OK} {label}")
        results["pass"] += 1
    elif warn:
        print(f"  {WARN} {label} — {msg_fail}")
        results["warn"] += 1
    else:
        print(f"  {FAIL} {label} — {msg_fail}")
        results["fail"] += 1


def main():
    print("=" * 55)
    print("  HFT Momentum Bot — Health Check")
    print("=" * 55)

    # ------------------------------------------
    # 1. Python version
    # ------------------------------------------
    print("\n[1/6] Python Version")
    v = sys.version_info
    ok = (v.major, v.minor) >= REQUIRED_PYTHON
    check(
        f"Python {v.major}.{v.minor}.{v.micro}",
        ok,
        f"Se requiere >= {REQUIRED_PYTHON[0]}.{REQUIRED_PYTHON[1]}",
    )

    # ------------------------------------------
    # 2. Virtual environment
    # ------------------------------------------
    print("\n[2/6] Virtual Environment")
    in_venv = sys.prefix != sys.base_prefix
    check(
        f"Ejecutando dentro de venv ({sys.prefix})",
        in_venv,
        "Activa el venv primero: venv\\Scripts\\activate.bat",
        warn=True,
    )

    # ------------------------------------------
    # 3. Paquetes requeridos
    # ------------------------------------------
    print("\n[3/6] Paquetes Requeridos")
    for pkg in REQUIRED_PACKAGES:
        try:
            mod = importlib.import_module(pkg)
            ver = getattr(mod, "__version__", "?")
            check(f"{pkg} ({ver})", True)
        except ImportError as e:
            check(pkg, False, f"pip install {pkg}  —  {e}")

    # ------------------------------------------
    # 4. Archivo .env
    # ------------------------------------------
    print("\n[4/6] Archivo .env")
    # Buscar .env relativo al script o en cwd
    env_candidates = [
        os.path.join(os.path.dirname(__file__), "..", ".env"),
        os.path.join(os.getcwd(), ".env"),
    ]
    env_path = None
    for candidate in env_candidates:
        if os.path.isfile(candidate):
            env_path = os.path.abspath(candidate)
            break

    if env_path:
        check(f".env encontrado en {env_path}", True)
        # Cargar y verificar variables
        from dotenv import load_dotenv
        load_dotenv(env_path)
        for var in REQUIRED_ENV_VARS:
            val = os.getenv(var)
            if val and val not in ("tu_password_aqui", "tu_password_db", "12345678"):
                check(f"  {var} = {'*' * min(len(val), 8)}", True)
            elif val:
                check(f"  {var}", False, "Tiene valor placeholder, reemplazar con valor real", warn=True)
            else:
                check(f"  {var}", False, "Variable no definida")
    else:
        check(".env", False, "No encontrado. Ejecuta: copy .env.example .env")

    # ------------------------------------------
    # 5. Directorio models/
    # ------------------------------------------
    print("\n[5/6] Modelo ML")
    models_dir = os.path.join(os.path.dirname(__file__), "..", "models")
    model_file = os.path.join(models_dir, "rf_classifier_v1.pkl")
    if os.path.isfile(model_file):
        size_mb = os.path.getsize(model_file) / (1024 * 1024)
        check(f"Modelo encontrado ({size_mb:.1f} MB)", True)
    else:
        check(
            "Modelo rf_classifier_v1.pkl",
            False,
            "No encontrado. Ejecuta: python scripts\\train_model.py",
            warn=True,
        )

    # ------------------------------------------
    # 6. PostgreSQL connection
    # ------------------------------------------
    print("\n[6/6] Conexion PostgreSQL")
    try:
        import psycopg2
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=os.getenv("DB_PORT", "5432"),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASS", ""),
            dbname=os.getenv("DB_NAME", "hft"),
            connect_timeout=5,
        )
        check("Conexion a PostgreSQL exitosa", True)

        # Verificar tablas
        with conn.cursor() as cur:
            cur.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema='public' AND table_name IN ('trade_logs', 'microstructure_logs')"
            )
            tables = [row[0] for row in cur.fetchall()]

        for t in ("trade_logs", "microstructure_logs"):
            if t in tables:
                check(f"  Tabla '{t}' existe", True)
            else:
                check(f"  Tabla '{t}'", False, "Ejecuta: scripts\\setup_db.bat")
        conn.close()
    except Exception as e:
        check("Conexion a PostgreSQL", False, str(e))

    # ------------------------------------------
    # Resumen
    # ------------------------------------------
    print("\n" + "=" * 55)
    total = results["pass"] + results["fail"] + results["warn"]
    print(f"  Resultados: {results['pass']}/{total} OK,  "
          f"{results['fail']} errores,  {results['warn']} advertencias")
    if results["fail"] == 0:
        print(f"  {OK} Entorno listo para produccion!")
    else:
        print(f"  {FAIL} Corrige los errores antes de arrancar el bot.")
    print("=" * 55)

    sys.exit(1 if results["fail"] > 0 else 0)


if __name__ == "__main__":
    main()
