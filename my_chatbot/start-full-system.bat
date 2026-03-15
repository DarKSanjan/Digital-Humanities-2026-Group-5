@echo off
REM Full System Launch - Backend + Frontend with Avatar
REM This starts both Python backend and React frontend

echo.
echo ========================================
echo   PERSUASIVE CHATBOT - FULL SYSTEM
echo ========================================
echo.
echo Starting complete system with:
echo   - Python backend (avatar rendering)
echo   - React frontend (UI)
echo   - Full conversation pipeline
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found!
    echo Please install Python 3.9+ and try again.
    pause
    exit /b 1
)

REM Check if Node.js is available
node --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Node.js not found!
    echo Please install Node.js 18+ and try again.
    pause
    exit /b 1
)

echo [1/3] Checking Python dependencies...
cd backend
python -c "import torch; import numpy; import PIL" >nul 2>&1
if errorlevel 1 (
    echo WARNING: Python dependencies not installed!
    echo Installing dependencies...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo ERROR: Failed to install Python dependencies
        pause
        exit /b 1
    )
)
cd ..

echo [2/3] Checking frontend dependencies...
cd frontend
if not exist "node_modules" (
    echo Installing frontend dependencies...
    npm install
    if errorlevel 1 (
        echo ERROR: Failed to install frontend dependencies
        pause
        exit /b 1
    )
)
cd ..

echo [3/3] Starting system...
echo.
echo ========================================
echo   SYSTEM STARTING
echo ========================================
echo.
echo Backend will start in a new window...
echo Frontend will start in this window...
echo.
echo IMPORTANT:
echo   - Keep both windows open
echo   - Avatar rendering requires backend
echo   - First startup may take 10-20 seconds
echo.

REM Start Python backend in new window
start "Persuasive Chatbot - Backend" cmd /k "cd backend && python src/main.py"

REM Wait a moment for backend to initialize
timeout /t 3 /nobreak >nul

REM Start frontend in this window
cd frontend
echo Starting frontend...
echo.
npm run dev:react

pause
