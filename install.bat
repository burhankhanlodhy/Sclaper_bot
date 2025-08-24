@echo off
echo Installing Kraken Paper Trading Bot dependencies...

:: Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python is not installed or not in PATH.
    echo Please install Python 3.8 or higher from https://python.org
    pause
    exit /b 1
)

:: Install required packages
echo Installing Python packages...
pip install -r requirements.txt

if %errorlevel% neq 0 (
    echo Failed to install dependencies.
    pause
    exit /b 1
)

echo.
echo Installation completed successfully!
echo.
echo To start the bot, run: start_bot.bat
echo The web interface will be available at: http://localhost:8080
echo.
pause
