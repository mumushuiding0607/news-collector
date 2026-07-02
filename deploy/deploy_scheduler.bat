@echo off
chcp 65001 >nul 2>&1
REM ================================================================
REM News Collector - Scheduler Deployment Script
REM ================================================================
REM
REM Deploy scheduler to remote server
REM
REM Usage:
REM   Run in cmd: deploy_scheduler.bat
REM ================================================================

setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%.."
set "DEPLOY_DIR=%SCRIPT_DIR%"
set "ENV_FILE=%DEPLOY_DIR%.env"

set "SERVER_IP="
set "SERVER_USER=admin"
set "SERVER_PORT=22"
set "REMOTE_PATH=/opt/backend"
set "SSH_KEY="

echo.
echo ================================================================
echo   Scheduler Deployment Script
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
        echo [ERROR] Config file is incomplete or SERVER_IP not set
        exit /b 1
    )
) else (
    echo [ERROR] Config file not found: %ENV_FILE%
    exit /b 1
)

REM ================================================================
REM Build SSH/SCP command
REM ================================================================
set "SSH_CMD=ssh"
set "SCP_CMD=scp"

if defined SSH_KEY (
    set "SSH_CMD=ssh -i !SSH_KEY!"
    set "SCP_CMD=scp -i !SSH_KEY!"
)

set "SSH_FULL=!SSH_CMD! -p !SERVER_PORT! -o LogLevel=ERROR -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=10 !SERVER_USER!@!SERVER_IP!"
set "SCP_FULL=!SCP_CMD! -P !SERVER_PORT! -o LogLevel=ERROR -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=10"

echo.
echo [CHECK] Checking required files...
if not exist "%PROJECT_ROOT%\backend\config\tasks.json" (
    echo [ERROR] tasks.json not found in backend\config
    exit /b 1
)
if not exist "%PROJECT_ROOT%\backend\run_scheduler.py" (
    echo [ERROR] run_scheduler.py not found
    exit /b 1
)
echo [OK] All files found

echo.
echo ================================================================
echo   Scheduler Deployment
echo ================================================================
echo   Server: !SERVER_USER!@!SERVER_IP!:!SERVER_PORT!
echo   Path:   !REMOTE_PATH!
echo ================================================================
echo [INFO] Proceeding with deployment...
echo.

echo [STEP 1] Stop existing scheduler...
!SSH_FULL! "pkill -f 'backend/run_scheduler.py' || true"
sleep 2
!SSH_FULL! "pkill -9 -f 'backend/run_scheduler.py' || true"
sleep 2
echo [OK] Old scheduler stopped

echo.
echo [STEP 2] Upload scheduler files...
echo [INFO] Uploading run_scheduler.py...
!SCP_FULL! "%PROJECT_ROOT%\backend\run_scheduler.py" !SERVER_USER!@!SERVER_IP!:%REMOTE_PATH%/backend/run_scheduler.py
echo [INFO] Uploading config directory...
!SCP_FULL! -r "%PROJECT_ROOT%\backend\config" !SERVER_USER!@!SERVER_IP!:%REMOTE_PATH%/backend/config
echo [OK] Upload complete

echo.
echo [STEP 3] Start scheduler in background...
!SSH_FULL! "mkdir -p '%REMOTE_PATH%/logs' && cd '%REMOTE_PATH%' && nohup python3 backend/run_scheduler.py >> '%REMOTE_PATH%/logs/scheduler.log' 2>&1 &"
echo [OK] Scheduler started

echo.
echo [STEP 4] Verify scheduler...
sleep 2
!SSH_FULL! "pgrep -f 'admin/scheduler/job_runner.py' > /dev/null 2>&1 && echo '[OK] Running' || echo '[WARN] Not running'"

echo.
echo [STEP 5] Show recent logs...
echo --- scheduler log (first 10 lines) ---
for /f "tokens=*" %%a in ('!SSH_FULL! "head -10 '%REMOTE_PATH%/logs/scheduler.log' 2>/dev/null || echo '(no log yet)'" 2^>nul') do echo %%a
echo --- application log ---
echo Log directory: %REMOTE_PATH%/logs/
for /f "tokens=*" %%a in ('!SSH_FULL! "ls -la '%REMOTE_PATH%/logs/' 2>/dev/null || echo '(logs dir not found)'" 2^>nul') do echo %%a
echo.

echo ================================================================
echo   Deployment Complete
echo ================================================================
for /f "tokens=*" %%a in ('!SSH_FULL! "echo Logs: tail -f '%REMOTE_PATH%/logs/scheduler.log'" 2^>nul') do echo   %%a
for /f "tokens=*" %%a in ('!SSH_FULL! "echo Stop: pkill -f 'backend/run_scheduler.py'" 2^>nul') do echo   %%a
echo ================================================================
