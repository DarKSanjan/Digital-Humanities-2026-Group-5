@echo off
REM Simple Web Launch - Persuasive Chatbot
REM This runs the app as a web application (simpler than Electron)

echo.
echo 🚀 Starting Persuasive Chatbot (Web Version)
echo.

REM Start backend
echo 🐍 Starting Python backend...
start "Backend - Python" cmd /k "cd backend && python src/main.py"

REM Wait for backend to initialize
timeout /t 3 /nobreak > nul

REM Start frontend (web only)
echo ⚛️  Starting React frontend...
start "Frontend - React" cmd /k "cd frontend && npm run dev:react"

echo.
echo ✅ Both services started!
echo.
echo 🌐 The browser should open automatically
echo    If not, open: http://localhost:5174
echo.
echo 📝 To stop: Close both command windows
echo.
pause
