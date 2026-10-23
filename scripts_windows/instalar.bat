@echo off
chcp 65001 >nul
title NovaEventos - Instalacion del Segundo Corte
cd /d "%~dp0.."

echo ============================================================================
echo   NOVA EVENTOS - INSTALACION DESDE CERO (SEGUNDO CORTE)
echo ============================================================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [1/4] Creando entorno virtual .venv...
    python -m venv .venv
    if errorlevel 1 (
        echo [ERROR] No se pudo crear el entorno virtual. Verifica que Python este instalado.
        pause
        exit /b 1
    )
) else (
    echo [1/4] Entorno virtual .venv detectado.
)

echo.
echo [2/4] Actualizando pip e instalando dependencias de requirements.txt...
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Fallo la instalacion de dependencias.
    pause
    exit /b 1
)

echo.
echo [3/4] Inicializando base de datos SQLite (reservas.db) con datos de prueba...
.\.venv\Scripts\python.exe -c "import almacen_sqlite; almacen_sqlite.inicializar_bd(); print('Base de datos reservas.db lista.')"

echo.
echo [4/4] Ejecutando pruebas automatizadas del sistema (pytest)...
.\.venv\Scripts\python.exe -m pytest test_sistema_eventos.py -v

echo.
echo ============================================================================
echo   INSTALACION COMPLETADA CON EXITO
echo   Ahora puedes ejecutar scripts_windows\iniciar.bat
echo ============================================================================
pause