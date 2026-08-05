@echo off
setlocal enabledelayedexpansion

title ARIA Setup

echo ===================================================
echo   ARIA - AI Research Assistant Setup
echo ===================================================
echo.

if not exist ".env" (
    echo [INFO] Creating .env file from .env.example...
    copy .env.example .env >nul
)

echo Please enter the full path to your Obsidian vault where ARIA should operate.
echo Example: C:\Users\YourName\Documents\ObsidianVault
set /p VAULT_PATH="Vault Path: "

if "!VAULT_PATH!"=="" (
    echo [ERROR] Vault path cannot be empty.
    pause
    exit /b 1
)

echo.
echo [INFO] Updating .env with your vault path...

:: PowerShell command to replace the vault path in .env
powershell -Command "(gc .env) -replace '^OBSIDIAN_VAULT_PATH=.*', 'OBSIDIAN_VAULT_PATH=!VAULT_PATH!' | Out-File -encoding ASCII .env"

echo [INFO] Starting ARIA using Docker...
docker-compose up -d --build

echo.
echo ===================================================
echo   Setup Complete!
echo   ARIA is now running in the background.
echo   Check your Obsidian vault for the new ARIA folders.
echo ===================================================
pause
