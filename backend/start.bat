@echo off
echo Starting AiPlatforma Backend...
cd /d %~dp0

if not exist ".env" (
    echo Creating .env from .env.example...
    copy .env.example .env
)

pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
