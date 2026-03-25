@echo off
cd /d C:\Users\Gustavo\ingresos_familiares_st

REM Kill existing processes
taskkill /F /IM streamlit.exe >nul 2>&1
taskkill /F /IM python.exe >nul 2>&1

REM Wait for cleanup
timeout /t 2 /nobreak >nul

REM Launch Streamlit in background and open browser
start /B python -m streamlit run app.py --server.port 8501

REM Wait and open browser
timeout /t 5 /nobreak >nul
start http://localhost:8501
