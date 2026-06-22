@echo off
title AiPlatforma - Backend
echo Starting Backend (port 8000)...
cd /d "%~dp0backend"
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
pause
