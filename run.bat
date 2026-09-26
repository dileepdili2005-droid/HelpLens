@echo off
setlocal enabledelayedexpansion

echo =====================================================================
echo           HelpLens - AI-Powered Everyday Problem Solver
echo =====================================================================
echo.

:: Detect Python executable
set "PY_CMD="

where python >nul 2>nul
if %errorlevel% equ 0 (
    set "PY_CMD=python"
    goto :FOUND_PYTHON
)

where py >nul 2>nul
if %errorlevel% equ 0 (
    set "PY_CMD=py"
    goto :FOUND_PYTHON
)

:: Check common Windows Python install locations
if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
    set "PY_CMD=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    goto :FOUND_PYTHON
)
if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    set "PY_CMD=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    goto :FOUND_PYTHON
)
if exist "%LOCALAPPDATA%\Programs\Mu Editor\Python\python.exe" (
    set "PY_CMD=%LOCALAPPDATA%\Programs\Mu Editor\Python\python.exe"
    goto :FOUND_PYTHON
)

echo [ERROR] Python was not found on your system!
echo Please install Python 3.8+ from https://www.python.org/downloads/
pause
exit /b 1

:FOUND_PYTHON
echo [INFO] Using Python: "!PY_CMD!"
"!PY_CMD!" --version

echo.
echo [1/3] Checking dependencies from requirements.txt...
"!PY_CMD!" -m pip install -q -r requirements.txt
if %errorlevel% neq 0 (
    echo [WARNING] Some dependencies might have had warnings, proceeding...
)

echo.
echo [2/3] Checking environment configuration...
if not exist ".env" (
    echo [INFO] Creating local .env from .env.example...
    copy ".env.example" ".env" >nul
)

echo.
echo [3/3] Starting HelpLens server...
echo.
echo =====================================================================
echo  * HelpLens is LIVE at: http://localhost:5000
echo  * Press Ctrl+C to stop the server
echo =====================================================================
echo.

"!PY_CMD!" app.py
pause
