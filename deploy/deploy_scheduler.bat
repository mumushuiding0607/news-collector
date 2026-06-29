@echo off
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

REM Convert Windows path to Unix style for tar
set "PROJECT_ROOT_UNIX=%PROJECT_ROOT:\=/%"

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

set "SSH_FULL=!SSH_CMD! -p !SERVER_PORT! -o LogLevel=ERROR !SERVER_USER!@!SERVER_IP!"
set "SCP_FULL=!SCP_CMD! -P !SERVER_PORT!"

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
REM Create tar packages locally first (exclude node_modules)
tar --exclude='admin/node_modules' --exclude='admin/.vite' --exclude='admin/dist' -cvf /tmp/admin.tar -C "%PROJECT_ROOT%" admin
tar -cvf /tmp/backend_config.tar -C "%PROJECT_ROOT%" backend/config

REM Upload via SCP
echo Uploading admin...
!SCP_FULL! /tmp/admin.tar "!SERVER_USER!@!SERVER_IP!:!REMOTE_PATH!/admin.tar"
echo Uploading backend config...
!SCP_FULL! /tmp/backend_config.tar "!SERVER_USER!@!SERVER_IP!:!REMOTE_PATH!/backend_config.tar"

REM Extract on remote
!SSH_FULL! "cd '%REMOTE_PATH%' && tar -xf admin.tar && tar -xf backend_config.tar && rm -f admin.tar backend_config.tar"
rm -f /tmp/admin.tar /tmp/backend_config.tar
echo [OK] Upload complete

echo.
echo [STEP 3] Start scheduler in background...
!SSH_FULL! "cd '%REMOTE_PATH%' && nohup python3 backend/run_scheduler.py >> /var/log/news_scheduler.log 2>&1 &"
echo [OK] Scheduler started

echo.
echo [STEP 4] Verify scheduler...
sleep 3
!SSH_FULL! "pgrep -f 'admin/scheduler/job_runner.py' > /dev/null 2>&1 && echo '[OK] Running' || echo '[WARN] Not running'"

echo.
echo [STEP 5] Show recent logs...
echo --- scheduler log (last 20 lines) ---
!SSH_FULL! "tail -20 /var/log/news_scheduler.log 2>/dev/null || echo '(no log yet)'"
echo --- application log ---
echo Log directory: %REMOTE_PATH%/logs/
!SSH_FULL! "ls -la %REMOTE_PATH%/logs/ 2>/dev/null || echo '(logs dir not found)'"
echo.
echo --- latest global.log (last 10 lines) ---
!SSH_FULL! "ls -t %REMOTE_PATH%/logs/*/global.log 2>/dev/null | head -1 | xargs tail -10 2>/dev/null || echo '(no global.log yet)'"
echo.

echo ================================================================
echo   Deployment Complete
echo ================================================================
echo   Logs:  !SSH_FULL! "tail -f /var/log/news_scheduler.log"
echo   Stop:   !SSH_FULL! "pkill -f 'backend/run_scheduler.py'"
echo ================================================================
