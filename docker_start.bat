@echo off
REM Start VcXsrv for X11 forwarding (ignore error if already running)
start "VcXsrv" /B "C:\Program Files\VcXsrv\vcxsrv.exe" :0 -multiwindow -clipboard -wgl -ac

REM Set DISPLAY environment variable for Docker
set DISPLAY=host.docker.internal:0.0

REM Build the Docker image (if not already built)
docker build -t ollama-image-app .

REM Run the Docker container with X11 forwarding and connect to native Ollama
REM --rm: remove container after exit
REM -e DISPLAY: pass display variable
REM -v: mount X11 socket (not needed on Windows, but included for reference)
docker run --rm -e DISPLAY=%DISPLAY% ollama-image-app

pause 