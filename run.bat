@echo off
setlocal
cd /d "%~dp0"

if /I "%~1"=="http" (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0deploy\run.ps1"
) else (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0deploy\run.ps1" -Https
)
set "EXIT_CODE=%ERRORLEVEL%"

if not "%EXIT_CODE%"=="0" (
  echo.
  echo Startup failed with exit code %EXIT_CODE%.
  pause
  exit /b %EXIT_CODE%
)

exit /b 0
