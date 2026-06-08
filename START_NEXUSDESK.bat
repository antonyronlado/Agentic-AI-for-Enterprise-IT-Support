@echo off
title NexusDesk Startup
color 0A
echo ============================================
echo    NexusDesk - Starting All Services...
echo ============================================
echo.

:: Check if MongoDB is running
echo [1/3] Checking MongoDB...
sc query MongoDB | find "RUNNING" >nul 2>&1
if %errorlevel% neq 0 (
    echo      MongoDB not running as service, attempting to start...
    net start MongoDB >nul 2>&1
    if %errorlevel% neq 0 (
        echo      Starting mongod manually...
        start "MongoDB" /min mongod --dbpath "C:\data\db"
        timeout /t 3 >nul
    )
) else (
    echo      MongoDB is already running.
)

echo.
echo [2/3] Starting Backend (FastAPI on port 8000)...
start "NexusDesk Backend" cmd /k "cd /d "%~dp0" && call env\Scripts\activate && cd backend && uvicorn main:app --reload --port 8000"

echo.
echo [3/3] Starting Frontend (React on port 3000)...
timeout /t 3 >nul
start "NexusDesk Frontend" cmd /k "cd /d "%~dp0client" && npm run dev"

echo.
echo ============================================
echo    All services started!
echo    Frontend: http://localhost:3000
echo    Backend:  http://localhost:8000
echo    API Docs: http://localhost:8000/docs
echo ============================================
echo.
echo Press any key to close this window...
pause >nul
