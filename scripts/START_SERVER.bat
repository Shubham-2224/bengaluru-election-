@echo off
title Voter Extraction Server
color 0A

echo.
echo ====================================================
echo    Voter Extraction - Python Server
echo ====================================================
echo.

cd /d "%~dp0\.."

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo ====================================================
    echo    ERROR: Python Not Found
    echo ====================================================
    echo.
    echo Python is not installed or not in your system PATH!
    echo.
    echo SOLUTION:
    echo 1. Download Python 3.8+ from: https://www.python.org/downloads/
    echo 2. During installation, CHECK the box:
    echo    "Add Python to PATH" or "Add Python to environment variables"
    echo 3. After installation, RESTART this batch file
    echo.
    echo ====================================================
    echo.
    echo Press any key to close this window...
    pause >nul
    exit /b 1
)

echo [OK] Python found
python --version

REM Check if backend directory exists
if not exist "backend\python-service" (
    echo.
    echo ====================================================
    echo    ERROR: Directory Not Found
    echo ====================================================
    echo.
    echo Python service directory not found!
    echo Expected location: backend\python-service
    echo.
    echo Make sure you are running this file from the project root.
    echo.
    echo ====================================================
    echo.
    echo Press any key to close this window...
    pause >nul
    exit /b 1
)

cd backend\python-service

REM Check if requirements.txt exists
if not exist "requirements.txt" (
    echo.
    echo ====================================================
    echo    ERROR: requirements.txt Not Found
    echo ====================================================
    echo.
    echo The requirements.txt file is missing!
    echo This file is needed to install Python dependencies.
    echo.
    echo Make sure you are in the correct directory:
    echo backend\python-service
    echo.
    echo ====================================================
    echo.
    echo Press any key to close this window...
    pause >nul
    exit /b 1
)

echo.
echo [1/3] Installing/Updating Python dependencies...
python -m pip install --upgrade pip --quiet
python -m pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo [WARNING] Some dependencies may have failed to install.
    echo Continuing anyway...
)

echo [OK] Dependencies ready

echo.
echo [2/3] Checking configuration...
if not exist ".env" (
    echo [INFO] .env file not found. Using defaults.
    echo [INFO] To configure Azure/Google APIs, copy env.example.txt to .env
) else (
    echo [OK] Configuration file found
)

echo.
echo [3/3] Starting Flask server...
echo.
echo ====================================================
echo    Server Information
echo ====================================================
echo Server URL:  http://localhost:5000
echo Frontend:    http://localhost:5000/
echo API Health:  http://localhost:5000/health
echo.
echo ====================================================
echo    Instructions
echo ====================================================
echo 1. Wait for "Server running on..." message
echo 2. Open browser to: http://localhost:5000
echo 3. Press Ctrl+C to stop the server
echo ====================================================
echo.

REM Wait a moment, then try to open browser
timeout /t 3 /nobreak >nul
start http://localhost:5000

REM Start the Flask server
python app.py

REM If server exits, show message
echo.
echo ====================================================
echo    Server Stopped
echo ====================================================
echo.
echo The server has been stopped.
echo To start again, double-click START_SERVER.bat
echo.
echo ====================================================
echo.
echo Press any key to close this window...
pause >nul

