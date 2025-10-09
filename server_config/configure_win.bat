@echo off
set SERVICE_NAME="Uvicorn Server - Bledot"
set APP_DIR="%~dp0\.."
set NSSM_PATH="%APP_DIR%\nssm.exe"
set STARTUP_SCRIPT="%APP_DIR%\temp\start_uvicorn.bat"

echo @echo off > %STARTUP_SCRIPT%
echo cd /d %%~dp0 >> %STARTUP_SCRIPT%
echo call bledot-env\Scripts\activate >> %STARTUP_SCRIPT%
echo uvicorn main:app >> %STARTUP_SCRIPT%

"%NSSM_PATH%" install %SERVICE_NAME% "cmd" "/c %STARTUP_SCRIPT%"

"%NSSM_PATH%" set %SERVICE_NAME% AppDirectory %APP_DIR%
"%NSSM_PATH%" set %SERVICE_NAME% Start SERVICE_AUTO_START

echo.
echo %SERVICE_NAME% installed successfully.
