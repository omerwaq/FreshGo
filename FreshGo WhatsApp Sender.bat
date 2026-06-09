@echo off
title FreshGo WhatsApp Bulk Sender
echo.
echo  =============================================
echo   Fresh Go - WhatsApp Bulk Sender (Windows)
echo  =============================================
echo.

cd /d "%~dp0"

:: Check if venv exists
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
) else (
    echo venv nahi mila. Installing dependencies...
    pip install selenium openpyxl webdriver-manager requests
)

python bulk_whatsapp.py

echo.
pause
