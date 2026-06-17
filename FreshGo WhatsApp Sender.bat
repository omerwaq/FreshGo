@echo off
title FreshGo WhatsApp Bulk Sender
echo.
echo  =============================================
echo   Fresh Go - WhatsApp Bulk Sender (Windows)
echo  =============================================
echo.

cd /d "%~dp0"

python --version >nul 2>&1
if errorlevel 1 goto nopython

echo Installing / checking packages...
python -m pip install --quiet selenium openpyxl webdriver-manager requests

echo.
python bulk_whatsapp.py
goto end

:nopython
echo ERROR: Python not found on this PC.
echo.
echo Please install Python from: https://python.org/downloads
echo During install, tick the box: "Add Python to PATH"
echo Then close and re-open this file.

:end
echo.
pause
