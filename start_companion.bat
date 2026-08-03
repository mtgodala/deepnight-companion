@echo off
title Deepnight Companion
cd /d "%~dp0"

rem server already running? just open the browser
netstat -ano | findstr ":8010" | findstr "LISTENING" >nul
if %errorlevel%==0 (
    start "" http://localhost:8010/
    exit /b 0
)

if exist .venv\Scripts\python.exe (
    set "PY=.venv\Scripts\python.exe"
) else (
    set "PY=py -3"
)

echo.
echo  Deepnight Companion - http://localhost:8010
echo  Closing this window stops the server.
echo.
%PY% run_companion.py
