@echo off
setlocal
title GrabKit Admin
cd /d "%~dp0"

set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY (
    where python >nul 2>nul && set "PY=python"
)
if not defined PY (
    echo.
    echo   GrabKit Admin needs Python: https://www.python.org/downloads/
    echo   Tick "Add python.exe to PATH" on the first screen.
    echo.
    start "" "https://www.python.org/downloads/"
    pause
    exit /b 1
)

for /f "delims=" %%i in ('%PY% -c "import sys,os;print(os.path.join(os.path.dirname(sys.executable),'pythonw.exe'))" 2^>nul') do set "PYW=%%i"
if exist "%PYW%" (
    start "" "%PYW%" "grabkit_admin.py"
) else (
    %PY% "grabkit_admin.py"
)
exit /b 0
