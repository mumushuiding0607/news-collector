@echo off
chcp 65001 >nul 2>&1
REM ================================================================
REM News Collector - Python Deployment Script
REM ================================================================
REM
REM Deploy to remote server using Python + uvicorn (no Docker)
REM
REM Usage:
REM   1. Double-click to run, or run in cmd: deploy_on_server.bat
REM   2. First run will guide you through configuration
REM   3. Subsequent runs will use saved configuration
REM ================================================================

setlocal enabledelayedexpansion

REM ================================================================
REM Configuration
REM ================================================================
set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%.."
set "DEPLOY_DIR=%SCRIPT_DIR%"
set "ENV_FILE=%DEPLOY_DIR%.env"

REM Default values
set "SERVER_IP="
set "SERVER_USER=admin"
set "SERVER_PORT=22"
set "REMOTE_PATH=/opt/app"
set "SSH_KEY="
set "SERVER_PYTHON=python3"

REM ================================================================
REM Load .env configuration
REM ================================================================
echo.
echo ================================================================
echo   News Collector - Deployment Script
echo ================================================================

if exist "%ENV_FILE%" (
    echo [INFO] Loading config: %ENV_FILE%
    for /f "usebackq tokens=1,* delims==" %%a in ("%ENV_FILE%") do (
        set "key=%%a"
        set "val=%%b"
        set "key=!key: =!"
        set "key=!key:#=!"
        if not "!key!"=="" (
            if "!key!"=="SERVER_IP" set "SERVER_IP=!val!"
            if "!key!"=="SERVER_USER" set "SERVER_USER=!val!"
            if "!key!"=="SERVER_PORT" set "SERVER_PORT=!val!"
            if "!key!"=="REMOTE_PATH" set "REMOTE_PATH=!val!"
            if "!key!"=="SSH_KEY" set "SSH_KEY=!val!"
        )
    )
    if defined SERVER_IP (
        echo [OK] Config loaded
        echo   SERVER_IP: !SERVER_IP!
        echo   SERVER_USER: !SERVER_USER!
        echo   REMOTE_PATH: !REMOTE_PATH!
    ) else (
        echo [WARN] Config file is incomplete, entering setup mode
    )
) else (
    echo [INFO] No config file found, entering setup mode
)

REM ================================================================
REM Setup wizard (if needed)
REM ================================================================
if not defined SERVER_IP (
    echo.
    echo ================================================================
    echo   First Time Setup
    echo ================================================================

    set /p SERVER_IP="Server public IP: "
    if "!SERVER_IP!"=="" (
        echo [ERROR] IP cannot be empty
        exit /b 1
    )

    set /p SERVER_USER="Server username [default admin]: "
    if "!SERVER_USER!"=="" set "SERVER_USER=admin"

    set /p SERVER_PORT="SSH port [default 22]: "
    if "!SERVER_PORT!"=="" set "SERVER_PORT=22"

    set /p REMOTE_PATH="Remote path [default /opt/backend]: "
    if "!REMOTE_PATH!"=="" set "REMOTE_PATH=/opt/backend"

    set /p SSH_KEY="SSH private key path (leave empty if none): "

    echo.
    set /p SAVE_CONFIG="Save config to .env for next time? (y/n): "
    if /i "!SAVE_CONFIG!"=="y" (
        (
            echo SERVER_IP=!SERVER_IP!
            echo SERVER_USER=!SERVER_USER!
            echo SERVER_PORT=!SERVER_PORT!
            echo REMOTE_PATH=!REMOTE_PATH!
            echo SSH_KEY=!SSH_KEY!
        ) > "!ENV_FILE!"
        echo [OK] Config saved to !ENV_FILE!
    )
)

REM ================================================================
REM Build SSH/SCP command prefix
REM ================================================================
set "SSH_CMD=ssh"
set "SCP_CMD=scp"
if defined SSH_KEY (
    set "SSH_CMD=ssh -i !SSH_KEY!"
    set "SCP_CMD=scp -i !SSH_KEY!"
)
set "SSH_FULL=!SSH_CMD! -p %SERVER_PORT% -o LogLevel=ERROR %SERVER_USER%@%SERVER_IP%"
set "SCP_FULL=!SCP_CMD! -P %SERVER_PORT%"

REM ================================================================
REM Check required files
REM ================================================================
echo.
echo [CHECK] Checking required files...

if not exist "%PROJECT_ROOT%\backend\requirements.txt" (
    echo [ERROR] requirements.txt not found
    exit /b 1
)
echo   [OK] requirements.txt

if not exist "%PROJECT_ROOT%\backend\main.py" (
    echo [ERROR] main.py not found
    exit /b 1
)
echo   [OK] main.py

if not exist "%PROJECT_ROOT%\backend\script\db\__init__.py" (
    echo [ERROR] script/db/__init__.py not found
    exit /b 1
)
echo   [OK] script/db/__init__.py

REM ================================================================
REM Confirm deployment
REM ================================================================
echo.
echo ================================================================
echo   Deployment Confirmation
echo ================================================================
echo   Server: !SERVER_USER!@!SERVER_IP!:!SERVER_PORT!
echo   Path:   !REMOTE_PATH!
if defined SSH_KEY echo   Key:   !SSH_KEY!
echo   Mode:   Python + uvicorn (no Docker)
echo ================================================================
REM Confirmation removed - auto-proceed

REM ================================================================
REM Step 1: Create remote directory
REM ================================================================
echo.
echo ================================================================
echo   Step 1: Create Remote Directory
echo ================================================================
!SSH_FULL! "mkdir -p '%REMOTE_PATH%'"
echo [OK] Directory created

REM ================================================================
REM Step 2: Upload requirements.txt
REM ================================================================
echo.
echo ================================================================
echo   Step 2: Upload requirements.txt
echo ================================================================
!SCP_FULL! "%PROJECT_ROOT%\backend\requirements.txt" %SERVER_USER%@!SERVER_IP!:%REMOTE_PATH%/requirements.txt
echo [OK] requirements.txt uploaded

REM ================================================================
REM Step 3: Install Python dependencies
REM ================================================================
echo.
echo ================================================================
echo   Step 3: Install Python Dependencies
echo ================================================================
echo [INFO] Remove system python3-rich (blocks pip)...
!SSH_FULL! "apt-get remove -y python3-rich 2>/dev/null || true"
echo [INFO] Installing packages...
!SSH_FULL! "cd '%REMOTE_PATH%' && LC_ALL=C python3 -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/ --no-cache-dir --break-system-packages --ignore-installed"
if errorlevel 1 (
    echo [ERROR] pip install failed, please check the error above
    exit /b 1
)
echo [OK] Dependencies installed

echo.
echo ================================================================
echo   Step 3b: Install Playwright Browsers
echo ================================================================
!SSH_FULL! "if [ -d '/root/.cache/ms-playwright' ]; then cd '%REMOTE_PATH%' && python3 -m playwright install chromium; fi"
echo [OK] Playwright check complete

REM ================================================================
REM Step 4: Upload project files
REM ================================================================
echo.
echo ================================================================
echo   Step 4: Upload Project Files
echo ================================================================

echo [INFO] Uploading .env...
if exist "%PROJECT_ROOT%\backend\.env" (
    !SCP_FULL! "%PROJECT_ROOT%\backend\.env" %SERVER_USER%@!SERVER_IP!:%REMOTE_PATH%/backend/.env
)

echo [INFO] Uploading backend directory...
!SCP_FULL! -r "%PROJECT_ROOT%\backend" %SERVER_USER%@!SERVER_IP!:%REMOTE_PATH%

echo [OK] Upload complete

echo.
echo ================================================================
echo   Step 4b: Stop old services
echo ================================================================
!SSH_FULL! "pkill -f 'uvicorn backend.main:app' 2>/dev/null || true; pkill -f 'run_scheduler' 2>/dev/null || true; echo 'old processes stopped'"
echo [OK] Old services stopped

REM ================================================================
REM Step 5-7: Start services
REM ================================================================
echo.
echo ================================================================
echo   Step 5-7: Start Backend and Scheduler
echo ================================================================
!SSH_FULL! "cd '%REMOTE_PATH%' && nohup python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 31234 > /var/log/news_collector.log 2>&1 &"
!SSH_FULL! "cd '%REMOTE_PATH%' && nohup python3 run_scheduler.py > /var/log/news_scheduler.log 2>&1 &"
!SSH_FULL! "sleep 3 && curl -s http://localhost:31234/api/health && echo '[OK] Backend is running' || echo '[ERROR] Backend not responding'"

echo.
echo ================================================================
echo   Deployment Log Output
echo ================================================================
echo --- Backend Service Log (last 5 lines) ---
for /f "tokens=*" %%a in ('!SSH_FULL! "tail -5 /var/log/news_collector.log 2>/dev/null || echo '(no log yet)'" 2^>nul') do echo %%a
echo.
echo --- Scheduler Process Log (last 10 lines) ---
for /f "tokens=*" %%a in ('!SSH_FULL! "tail -10 /var/log/news_scheduler.log 2>/dev/null || echo '(no scheduler log yet)'" 2^>nul') do echo %%a
echo.
echo --- Application Logs Directory ---
for /f "tokens=*" %%a in ('!SSH_FULL! "ls -la '%REMOTE_PATH%/logs/' 2>/dev/null || echo '(no logs directory)'" 2^>nul') do echo %%a
echo.
echo --- Latest Global Log (last 5 lines) ---
for /f "tokens=*" %%a in ('!SSH_FULL! "ls -t '%REMOTE_PATH%/logs/'/*/global.log 2>/dev/null | head -1 | xargs tail -5 2>/dev/null || echo '(no global.log yet)'" 2^>nul') do echo %%a
echo.
REM Step 8: Save requirements.txt as baseline for next diff
REM ================================================================
echo.
echo ================================================================
echo   Step 8: Save Baseline
echo ================================================================
!SCP_FULL! "%PROJECT_ROOT%\backend\requirements.txt" "!SERVER_USER!@!SERVER_IP!:%REMOTE_PATH%/requirements.txt"
echo [OK] Baseline saved

REM ================================================================
REM Complete
REM ================================================================
echo.
echo ================================================================
echo   Deployment Complete!
echo ================================================================
echo   Access:   http://!SERVER_IP!:31234/api/health
for /f "tokens=*" %%a in ('!SSH_FULL! "echo Logs: tail -f /var/log/news_collector.log" 2^>nul') do echo   %%a
for /f "tokens=*" %%a in ('!SSH_FULL! "echo Stop: pkill -f 'uvicorn backend.main:app'" 2^>nul') do echo   %%a
for /f "tokens=*" %%a in ('!SSH_FULL! "echo Scheduler: tail -f /var/log/news_scheduler.log" 2^>nul') do echo   %%a
echo ================================================================
