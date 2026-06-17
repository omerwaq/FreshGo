@echo off
title FreshGo - Auto Update
echo.
echo  =============================================
echo   FreshGo - Automatic Update from GitHub
echo  =============================================
echo.
echo  Updating... please wait...
echo.

:: Download latest ZIP from GitHub using PowerShell (built into Windows)
powershell -Command "Invoke-WebRequest -Uri 'https://github.com/omerwaq/FreshGo/archive/refs/heads/main.zip' -OutFile '%TEMP%\freshgo_update.zip'" 2>nul

if not exist "%TEMP%\freshgo_update.zip" (
    echo  ERROR: Download failed. Check your internet connection.
    pause
    exit /b 1
)

:: Extract ZIP
powershell -Command "Expand-Archive -Path '%TEMP%\freshgo_update.zip' -DestinationPath '%TEMP%\freshgo_extracted' -Force" 2>nul

:: Copy updated files to current folder
powershell -Command "Copy-Item '%TEMP%\freshgo_extracted\FreshGo-main\*.py' '%~dp0' -Force"
powershell -Command "Copy-Item '%TEMP%\freshgo_extracted\FreshGo-main\*.bat' '%~dp0' -Force"
powershell -Command "Copy-Item '%TEMP%\freshgo_extracted\FreshGo-main\*.html' '%~dp0' -Force"
powershell -Command "Copy-Item '%TEMP%\freshgo_extracted\FreshGo-main\*.toml' '%~dp0' -Force"

:: Cleanup temp files
powershell -Command "Remove-Item '%TEMP%\freshgo_update.zip' -Force" 2>nul
powershell -Command "Remove-Item '%TEMP%\freshgo_extracted' -Recurse -Force" 2>nul

echo  =============================================
echo   Update complete! Latest code downloaded.
echo  =============================================
echo.
pause
