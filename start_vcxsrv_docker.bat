@echo off
REM Start VcXsrv if not already running
set VCSXSRV_PATH=%ProgramFiles%\VcXsrv\vcxsrv.exe
set VCSXSRV_ARGS=-multiwindow -ac -clipboard -wgl -dpi auto -screen 0 1920x1080

REM Check if VcXsrv is running
TASKLIST /FI "IMAGENAME eq vcxsrv.exe" 2>NUL | find /I /N "vcxsrv.exe">NUL
if "%ERRORLEVEL%"=="1" (
    echo Starting VcXsrv X server...
    start "VcXsrv" "%VCSXSRV_PATH%" %VCSXSRV_ARGS%
    timeout /t 2 >nul
) else (
    echo VcXsrv is already running.
)

REM Start the Docker Compose app (only the app container; Ollama must be running natively)
call docker compose up
pause 