@echo off
REM News Collection Project - Initialization Script
REM Usage: Double-click to run or execute in cmd: init.bat

echo ==================================
echo News Collection Project - Init
echo ==================================

REM Install Python dependencies
echo.
echo [1/3] Installing Python dependencies...
pip install -r requirements.txt

REM Check if Flutter is installed
where flutter >nul 2>&1
if %errorlevel% equ 0 (
    echo.
    echo [2/3] Installing Flutter dependencies...
    cd news_board_app
    call flutter pub get
    cd ..
    echo Flutter dependencies installed
) else (
    echo.
    echo [2/3] Flutter not found, skipping Flutter dependencies
)

REM Run init_db.py
echo.
echo [3/3] Initializing database...
python init_db.py

echo.
echo ==================================
echo Init complete!
echo ==================================
pause
