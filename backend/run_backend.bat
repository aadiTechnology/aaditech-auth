@echo off
cd /d "%~dp0"
if not exist .env (
  if exist env (
    echo Creating .env from env...
    copy /Y env .env >nul
  ) else (
    echo Missing .env. Copy .env.example to .env and set DATABASE_URL, JWT_SECRET, and CORS_ORIGINS.
    pause
    exit /b 1
  )
)
if exist venv (
  echo Removing existing virtual environment...
  REM rmdir /s /q venv
)
echo Creating virtual environment...
python -m venv venv
call venv\Scripts\activate
echo install requirement.txt
pip install -r requirements.txt
echo Starting FastAPI server (test)...
uvicorn app.main:app --host 127.0.0.1 --port 8000
pause