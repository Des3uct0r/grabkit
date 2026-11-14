@echo off
setlocal
title GrabKit Desktop
cd /d "%~dp0"

set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY (
    where python >nul 2>nul && set "PY=python"
)
if not defined PY (
    echo.
    echo   GrabKit needs Python, which is free and takes 2 minutes to install.
    echo.
    echo   Opening https://www.python.org/downloads/ now.
    echo   IMPORTANT: tick "Add python.exe to PATH" on the first screen.
    echo.
    start "" "https://www.python.org/downloads/"
    pause
    exit /b 1
)

rem pythonw keeps the black console window out of the way
for /f "delims=" %%i in ('%PY% -c "import sys,os;print(os.path.join(os.path.dirname(sys.executable),'pythonw.exe'))" 2^>nul') do set "PYW=%%i"
if exist "%PYW%" (
    start "" "%PYW%" "grabkit_gui.py"
) else (
    %PY% "grabkit_gui.py"
)
exit /b 0
