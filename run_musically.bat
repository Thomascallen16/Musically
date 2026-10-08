@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [Musically] Creating local environment...
  py -3 -m venv .venv
  if errorlevel 1 python -m venv .venv
  call ".venv\Scripts\python.exe" -m pip install --upgrade pip
  call ".venv\Scripts\python.exe" -m pip install -r requirements.txt
  call ".venv\Scripts\python.exe" -m playwright install chromium
)

call ".venv\Scripts\python.exe" musically.py
