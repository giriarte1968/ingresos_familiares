@echo off
title Lanzador de Gestor de Ingresos Familiares
echo ================================================
echo Lanzando Gestor de Ingresos Familiares
echo ================================================
echo.

REM Kill any existing Streamlit and Python processes related to our app
echo Paso 1: Terminando procesos existentes...
taskkill /F /IM streamlit.exe >nul 2>&1
taskkill /F /IM python.exe >nul 2>&1

REM Force kill all Python processes to ensure clean state
echo Paso 2: Forzando terminacion de procesos Python...
wmic process where "name='python.exe'" call terminate >nul 2>&1

REM Clean pycache directory
echo Paso 3: Limpiando cache...
if exist __pycache__ rmdir /s /q __pycache__ >nul 2>&1
if exist .streamlit rmdir /s /q .streamlit >nul 2>&1

REM Use PowerShell to forcefully release the port
echo Paso 4: Liberando puerto 8503 con PowerShell...
powershell -Command "Get-NetTCPConnection -LocalPort 8503 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }"

REM Wait a moment for Windows to release resources
echo Paso 5: Esperando liberacion del puerto...
ping -n 2 127.0.0.1 >nul 2>&1

REM Verify port is free
echo Paso 6: Verificando estado del puerto 8503...
netstat -ano | findstr :8503 | findstr LISTEN >nul
if not errorlevel 1 (
    echo ADVERTENCIA: Puerto 8503 sigue en uso. Usando puerto alternativo 8505...
    set PUERTO=8505
) else (
    echo   Puerto 8503 libre.
    set PUERTO=8503
)

REM Start the Streamlit application
echo.
echo Paso 7: Iniciando la aplicacion en puerto %PUERTO%...
echo   Ejecutando: streamlit run app.py --server.port %PUERTO%
echo.
echo   La aplicacion estara disponible en: http://localhost:%PUERTO%
echo   Presiona Ctrl+C para detener la aplicacion cuando quieras terminar.
echo.

REM Run Streamlit
streamlit run app.py --server.port %PUERTO%

echo.
echo ================================================
echo La aplicacion ha terminado.
echo ================================================
pause
