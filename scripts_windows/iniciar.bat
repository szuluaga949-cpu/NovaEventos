@echo off
chcp 65001 >nul
title NovaEventos - Lanzador de Dos Terminales
cd /d "%~dp0.."

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] No se encontro el entorno virtual .venv.
    echo Ejecuta primero scripts_windows\instalar.bat
    pause
    exit /b 1
)

if "%CHATBOT_API_URL%"=="" set CHATBOT_API_URL=http://127.0.0.1:8011
if "%GROQ_MODEL%"=="" set GROQ_MODEL=llama-3.3-70b-versatile

echo ============================================================================
echo   INICIANDO NOVA EVENTOS (FASTAPI + GRADIO + SQLITE)
echo ============================================================================
echo   - Terminal 1 (FastAPI): http://127.0.0.1:8011/docs
echo   - Terminal 2 (Gradio) : http://127.0.0.1:7860
echo ============================================================================
echo.

echo [1/2] Abriendo Terminal 1: API del negocio en FastAPI (Puerto 8011)...
start "Terminal 1 - NovaEventos FastAPI (8011)" cmd /k "cd /d "%CD%" && .\.venv\Scripts\python.exe -m uvicorn main:app --reload --port 8011"

timeout /t 3 /nobreak >nul

echo [2/2] Abriendo Terminal 2: Interfaz conversacional en Gradio (Puerto 7860)...
start "Terminal 2 - NovaEventos Gradio (7860)" cmd /k "cd /d "%CD%" && set CHATBOT_API_URL=%CHATBOT_API_URL% && set GROQ_MODEL=%GROQ_MODEL% && .\.venv\Scripts\python.exe app_gradio.py"

timeout /t 4 /nobreak >nul
start http://127.0.0.1:7860
start http://127.0.0.1:8011/docs

echo.
echo Ambas terminales estan en ejecucion.