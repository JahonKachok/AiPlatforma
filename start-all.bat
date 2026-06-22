@echo off
title AiPlatforma - Launcher
echo ================================
echo   AiPlatforma - Starting...
echo ================================

echo [1/2] Starting Backend (port 8000)...
start "AiPlatforma Backend" cmd /k "cd /d "%~dp0backend" && python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

timeout /t 3 /nobreak >nul

echo [2/2] Starting Frontend (port 5173)...
start "AiPlatforma Frontend" cmd /k "cd /d "%~dp0" && npm run dev"

echo ================================
echo  Backend:  http://localhost:8000
echo  Frontend: http://localhost:5173
echo ================================
timeout /t 5 /nobreak >nul

start http://localhost:5173
