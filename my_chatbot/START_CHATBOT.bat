@echo off
setlocal enabledelayedexpansion

echo.
echo ========================================
echo   PERSUASIVE CHATBOT - LAUNCHER
echo ========================================
echo.

set "ROOT=%~dp0"

echo [1/3] Installing Python dependencies...
pip install websockets Pillow pyaudio pydub requests audioop-lts >nul 2>&1
echo Done.

echo [2/3] Checking API keys...
if not exist "%ROOT%frontend\.env" (
    echo ERROR: frontend\.env not found!
    echo Create it with your API keys.
    pause
    exit /b 1
)
echo Done.

echo [3/3] Launching chatbot...
echo.
echo ==========================================
echo   The chatbot window will open shortly.
echo   Hold the mic button to speak.
echo   Close the window to exit.
echo ==========================================
echo.

pushd "%ROOT%backend"
if exist "venv_cuda\Scripts\python.exe" (
    echo Using CUDA virtual environment...
    venv_cuda\Scripts\python.exe src/chatbot_app.py
) else (
    echo Using system Python...
    python src/chatbot_app.py
)
popd

pause
