@echo off
echo Starting Kraken Paper Trading Bot...
echo.
echo Web interface will be available at: http://localhost:8080
echo Press Ctrl+C to stop the bot
echo.

python main.py

if %errorlevel% neq 0 (
    echo.
    echo Bot stopped with error. Check the logs above.
    pause
)
