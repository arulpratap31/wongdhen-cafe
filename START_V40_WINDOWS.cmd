@echo off
setlocal
cd /d "%~dp0"
set "ENVIRONMENT=development"
title Wongdhen Cafe V40 - Dedicated Role Portals
cls
echo =======================================================
echo   WONGDHEN CAFE V40 - DEDICATED ROLE PORTALS
 echo =======================================================
echo.
echo WEBSITE:  http://127.0.0.1:8765/
echo LOGIN:    http://127.0.0.1:8765/admin
echo OWNER:    http://127.0.0.1:8765/owner
echo MANAGER:  http://127.0.0.1:8765/manager
echo RECEPTION: http://127.0.0.1:8765/staff/reservations
echo KITCHEN:   http://127.0.0.1:8765/staff/kitchen
echo CONTENT:   http://127.0.0.1:8765/staff/content
echo ACCOUNT:  http://127.0.0.1:8765/account
echo.
if not exist ".env" (
  echo FIRST RUN: .env is missing.
  echo Copy .env.example to .env and set your secure admin login and SESSION_SECRET.
  echo Optional: configure Google OAuth keys in .env.
  pause
  exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
  where py >nul 2>nul
  if not errorlevel 1 (py -3 -m venv .venv) else (python -m venv .venv)
  if errorlevel 1 (echo Python 3.11 or later is required. & pause & exit /b 1)
)
if not exist ".venv\.v40_dependencies_ready" (
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt
  if errorlevel 1 (echo Dependency installation failed. & pause & exit /b 1)
  echo ready > ".venv\.v40_dependencies_ready"
)
".venv\Scripts\python.exe" -u run_v40.py
if errorlevel 1 (echo V40 stopped or could not start. See error above. & pause & exit /b 1)
echo Server stopped. You can close this window.
pause
endlocal
