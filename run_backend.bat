@echo off
title ARIA - AI Research Assistant Server
echo ===================================================
echo   Starting ARIA Backend Service for Obsidian
echo ===================================================
echo.
cd /d "%~dp0backend"
if exist venv\Scripts\activate.bat (
    if exist venv\Scripts\uvicorn.exe (
        call venv\Scripts\activate.bat
    ) else (
        echo [INFO] Virtual environment detected but uvicorn missing. Installing dependencies...
        call venv\Scripts\activate.bat
        python -m pip install -r requirements.txt
    )
)
echo Server starting on http://localhost:8080...
echo Watching Vault: G:\Obsedian Files\ARIA
echo.
python -m uvicorn main:app --host 0.0.0.0 --port 8080 --reload
pause