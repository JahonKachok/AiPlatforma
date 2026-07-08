@echo off
title AiPlatforma - Launcher
echo ================================
echo   AiPlatforma - Starting...
echo ================================

start "AiPlatforma" cmd /k "cd /d "%~dp0" && .venv\Scripts\python.exe manage.py runserver 0.0.0.0:8000"

echo ================================
echo  App: http://localhost:8000
echo ================================
timeout /t 3 /nobreak >nul

start http://localhost:8000
