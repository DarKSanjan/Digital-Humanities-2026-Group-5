@echo off
REM Setup script for Persuasive Chatbot project (Windows)

echo Setting up Persuasive Chatbot project...

REM Check prerequisites
echo Checking prerequisites...

where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Python is not installed. Please install Python 3.9 or higher.
    exit /b 1
)

where node >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Node.js is not installed. Please install Node.js 18 or higher.
    exit /b 1
)

echo Prerequisites check passed

REM Setup backend
echo.
echo Setting up Python backend...
cd backend

if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo Installing Python dependencies...
python -m pip install --upgrade pip
pip install -r requirements.txt

if not exist ".env" (
    echo Creating .env file from template...
    copy .env.example .env
    echo Please edit backend\.env and configure your settings
)

cd ..

REM Setup frontend
echo.
echo Setting up Electron/React frontend...
cd frontend

echo Installing Node.js dependencies...
call npm install

if not exist ".env" (
    echo Creating .env file from template...
    copy .env.example .env
    echo Please edit frontend\.env and add your API keys
)

cd ..

echo.
echo Setup complete!
echo.
echo Next steps:
echo 1. Edit backend\.env with your configuration
echo 2. Edit frontend\.env with your API keys:
echo    - VITE_WHISPER_API_KEY
echo    - VITE_ELEVENLABS_API_KEY
echo    - VITE_LLM_API_KEY
echo 3. Download talking-head-anime-3 model (see backend\README.md)
echo.
echo To run the application:
echo    Terminal 1: cd backend ^&^& venv\Scripts\activate ^&^& python src\main.py
echo    Terminal 2: cd frontend ^&^& npm run dev

pause
