@echo off
title FreshGo WhatsApp Bulk Sender
chcp 65001 >nul
echo.
echo  =============================================
echo   Fresh Go - WhatsApp Bulk Sender (Windows)
echo  =============================================
echo.

cd /d "%~dp0"

:: Check Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found!
    echo Please install Python from https://python.org
    echo Make sure to tick "Add Python to PATH" during install.
    echo.
    pause
    exit /b 1
)

:: Activate venv if it exists, otherwise install packages globally
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
    echo venv activated.
) else (
    echo Installing required packages (first time only)...
    python -m pip install --quiet selenium openpyxl webdriver-manager requests
    if errorlevel 1 (
        echo ERROR: Could not install packages. Run as Administrator and try again.
        pause
        exit /b 1
    )
)

echo.
python bulk_whatsapp.py

echo.
pause
