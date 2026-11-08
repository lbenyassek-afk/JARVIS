@echo off
cd /d "%~dp0"
title JARVIS V8 Installer
py install.py
if errorlevel 1 (
  echo.
  echo Installation failed. Copy the error above.
  pause
  exit /b 1
)
echo.
echo JARVIS V8 is ready on your Desktop.
pause
