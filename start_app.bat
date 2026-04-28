@echo off
setlocal

cd /d "%~dp0"

start "CRISP-DM Regression Explorer" cmd /k "python -m streamlit run app.py --server.port 8501"

endlocal
