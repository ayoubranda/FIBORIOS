@echo off
title Fibrios Setup
echo ============================================
echo  FIBRIOS - Installing Dependencies
echo ============================================
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH.
    echo Please install Python from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

echo [1/4] Installing streamlit...
pip install streamlit
echo.

echo [2/4] Installing anthropic...
pip install anthropic
echo.

echo [3/4] Installing tvdatafeed...
pip install tvdatafeed
echo.

echo [4/4] Installing pandas...
pip install pandas
echo.

echo ============================================
echo  Setup complete! Run launch.bat to start.
echo ============================================
pause
