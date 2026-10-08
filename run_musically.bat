@echo off
setlocal
cd /d "%~dp0"

if not exist "Musically.exe" (
  echo This USB-ready copy is missing Musically.exe.
  echo Download the latest Musically USB package from GitHub Actions.
  pause
  exit /b 1
)

start "" "%~dp0Musically.exe"
