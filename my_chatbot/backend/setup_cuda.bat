@echo off
echo ========================================
echo CUDA PyTorch Setup for RTX 3080
echo ========================================
echo.

REM Check if Python 3.12 is available
where python312 >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo Found Python 3.12!
    set PYTHON_CMD=python312
    goto :create_venv
)

REM Check if Python 3.11 is available
where python311 >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo Found Python 3.11!
    set PYTHON_CMD=python311
    goto :create_venv
)

REM Check if Python 3.10 is available
where python310 >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo Found Python 3.10!
    set PYTHON_CMD=python310
    goto :create_venv
)

REM Check common installation paths
if exist "C:\Python312\python.exe" (
    echo Found Python 3.12 at C:\Python312\
    set PYTHON_CMD=C:\Python312\python.exe
    goto :create_venv
)

if exist "C:\Python311\python.exe" (
    echo Found Python 3.11 at C:\Python311\
    set PYTHON_CMD=C:\Python311\python.exe
    goto :create_venv
)

if exist "C:\Python310\python.exe" (
    echo Found Python 3.10 at C:\Python310\
    set PYTHON_CMD=C:\Python310\python.exe
    goto :create_venv
)

echo ERROR: Python 3.10, 3.11, or 3.12 not found!
echo.
echo Please install Python 3.12 from: https://www.python.org/downloads/
echo Make sure to check "Add Python to PATH" during installation.
echo.
pause
exit /b 1

:create_venv
echo.
echo Creating virtual environment with %PYTHON_CMD%...
%PYTHON_CMD% -m venv venv_cuda

echo.
echo Activating virtual environment...
call venv_cuda\Scripts\activate.bat

echo.
echo Upgrading pip...
python -m pip install --upgrade pip

echo.
echo Installing PyTorch with CUDA 12.1...
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

echo.
echo Installing project dependencies...
pip install -r requirements.txt

echo.
echo Installing additional dependencies...
pip install matplotlib scipy huggingface_hub

echo.
echo ========================================
echo Setup Complete!
echo ========================================
echo.
echo To verify CUDA is working, run:
echo   python check_cuda.py
echo.
echo To start the backend, run:
echo   python src/main.py
echo.
echo Remember to activate the environment first:
echo   venv_cuda\Scripts\activate.bat
echo.
pause
