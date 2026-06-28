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
        echo [WARN] Config file is incomplete
    )
) else (
    echo [INFO] No config file found
)

if not defined SERVER_IP (
    echo.
    echo [SETUP] Enter server configuration
    set /p SERVER_IP="Server IP: "
    if "!SERVER_IP!"=="" (
        echo [ERROR] IP cannot be empty
        exit /b 1
    )
    set /p SERVER_USER="Server username [admin]: "
    if "!SERVER_USER!"=="" set "SERVER_USER=admin"
    set /p SERVER_PORT="SSH port [22]: "
    if "!SERVER_PORT!"=="" set "SERVER_PORT=22"
    set /p REMOTE_PATH="Remote path [/opt/backend]: "
    if "!REMOTE_PATH!"=="" set "REMOTE_PATH=/opt/backend"
    set /p SSH_KEY="SSH key path (empty if none): "
)

REM ================================================================
REM Build SSH/SCP command
REM 注意：参数顺序必须是 -p port 在 -i key 之前
REM ================================================================
if defined SSH_KEY (
    set "SSH_FULL=ssh -p !SERVER_PORT! -i "!SSH_KEY!" !SERVER_USER!@!SERVER_IP!"
    set "SCP_FULL=scp -P !SERVER_PORT! -i "!SSH_KEY!"
) else (
    set "SSH_FULL=ssh -p !SERVER_PORT! !SERVER_USER!@!SERVER_IP!"
    set "SCP_FULL=scp -P !SERVER_PORT!"
)

echo.
echo [CHECK] Checking required files...
if not exist "%PROJECT_ROOT%\admin\scheduler\tasks.json" (
    echo [ERROR] tasks.json not found
    exit /b 1
)
if not exist "%PROJECT_ROOT%\backend\run_scheduler.py" (
    echo [ERROR] run_scheduler.py not found
    exit /b 1
)
echo [OK] All files found

echo.
echo ================================================================
echo   Deployment Confirmation
echo ================================================================
echo   Server: !SERVER_USER!@!SERVER_IP!:!SERVER_PORT!
echo   Path:   !REMOTE_PATH!
echo ================================================================
set /p CONFIRM="Continue? (y/n): "
if /i not "!CONFIRM!"=="y" (
    echo Cancelled
    exit /b 0
)

echo.
echo [STEP 1] Stop existing scheduler...
!SSH_FULL! "pkill -f 'backend/run_scheduler.py' || true"
timeout /t 2 /nobreak >nul
!SSH_FULL! "pkill -9 -f 'backend/run_scheduler.py' || true"
timeout /t 2 /nobreak >nul
echo [OK] Old scheduler stopped

echo.
echo [STEP 2] Upload scheduler files...
!SCP_FULL! -r "%PROJECT_ROOT%\admin" "!SERVER_USER!@!SERVER_IP!:%REMOTE_PATH%/admin"
!SCP_FULL! "%PROJECT_ROOT%\backend\run_scheduler.py" "!SERVER_USER!@!SERVER_IP!:%REMOTE_PATH%/backend/run_scheduler.py"
echo [OK] Upload complete

echo.
echo [STEP 3] Start scheduler in background...
!SSH_FULL! "cd '%REMOTE_PATH%' && nohup python3 backend/run_scheduler.py >> /var/log/news_scheduler.log 2>&1 &"
echo [OK] Scheduler started

echo.
echo [STEP 4] Verify scheduler...
timeout /t 3 /nobreak >nul
!SSH_FULL! "pgrep -f 'admin/scheduler/job_runner.py' > /dev/null 2>&1 && echo '[OK] Running' || echo '[WARN] Not running'"

echo.
echo [STEP 5] Show log output...
echo --- scheduler log (last 10 lines) ---
!SSH_FULL! "tail -10 /var/log/news_scheduler.log 2>/dev/null || echo '(no log yet)'"
echo --- application log ---
echo Log directory: %REMOTE_PATH%/logs/
!SSH_FULL! "ls -la %REMOTE_PATH%/logs/ 2>/dev/null || echo '(logs dir not found)'"
echo.
echo --- latest global.log ---
!SSH_FULL! "ls -t %REMOTE_PATH%/logs/*/global.log 2>/dev/null | head -1 | xargs tail -5 2>/dev/null || echo '(no global.log yet)'"
echo.

echo ================================================================
echo   Deployment Complete
echo ================================================================
echo   Logs:  !SSH_FULL! "tail -f /var/log/news_scheduler.log"
echo   Stop:   !SSH_FULL! "pkill -f 'backend/run_scheduler.py'"
echo ================================================================
