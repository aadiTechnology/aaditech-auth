@echo off
cd /d "%~dp0"
set ENV_FILE=.env.test
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
uvicorn app.main:app --host 127.0.0.1 --port 8022
pause