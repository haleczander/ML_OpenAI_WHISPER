@echo off
setlocal
cd /d "%~dp0"

echo Installing ML_OpenAI_WHISPER...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0deploy\install.ps1"
set "EXIT_CODE=%ERRORLEVEL%"

if not "%EXIT_CODE%"=="0" (
  echo.
  echo Installation failed with exit code %EXIT_CODE%.
  pause
  exit /b %EXIT_CODE%
)

echo.
echo Installation completed.
pause
exit /b 0
