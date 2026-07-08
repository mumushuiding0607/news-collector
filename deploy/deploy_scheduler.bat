@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%.."
set "ENV_FILE=%SCRIPT_DIR%.env"

set "SERVER_IP="
set "SERVER_USER=root"
set "SERVER_PORT=22"
set "REMOTE_PATH=/opt/app"

echo =================================================================
echo   Scheduler Deployment Script
echo =================================================================

if exist "%ENV_FILE%" (
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
        echo [OK] Config loaded: !SERVER_USER!@!SERVER_IP!:!SERVER_PORT! - !REMOTE_PATH!
    ) else (
        echo [ERROR] Config file incomplete
        exit /b 1
    )
) else (
    echo [ERROR] Config file not found: %ENV_FILE%
    exit /b 1
)

for /f "tokens=*" %%i in ('powershell -Command "Get-Date -Format 'yyyy-MM-dd'"') do set "TODAY=%%i"

set "SSH_KEY_ABS="
set "SSH_KEY_UNIX="
if defined SSH_KEY (
    set "SSH_KEY_FULL=!PROJECT_ROOT!\!SSH_KEY!"
    for /f "delims=" %%i in ('powershell -Command "[System.IO.Path]::GetFullPath('!SSH_KEY_FULL!')"') do set "SSH_KEY_ABS=%%i"
    for /f "delims=" %%i in ('bash -c "cygpath -u '!SSH_KEY_ABS!'"') do set "SSH_KEY_UNIX=%%i"
    if defined SSH_KEY_ABS icacls "!SSH_KEY_ABS!" /inheritance:r /grant:r "!USERNAME!:R" >nul 2>&1
)

if not exist "%PROJECT_ROOT%\backend\config\tasks.json" echo [ERROR] tasks.json not found && exit /b 1
if not exist "%PROJECT_ROOT%\backend\run_scheduler.py" echo [ERROR] run_scheduler.py not found && exit /b 1
echo [OK] Files found

echo =================================================================
echo   Server: !SERVER_USER!@!SERVER_IP!:!SERVER_PORT!
echo   Path:   !REMOTE_PATH!
if defined SSH_KEY_UNIX echo   Key:   !SSH_KEY_UNIX!
if not defined SSH_KEY_UNIX if defined SSH_KEY_ABS echo   Key:   !SSH_KEY_ABS!
echo =================================================================
echo.

echo [STEP 1] Stop scheduler...
ssh -p !SERVER_PORT! -o LogLevel=ERROR -o StrictHostKeyChecking=no -i !SSH_KEY_ABS! !SERVER_USER!@!SERVER_IP! "pkill -f 'backend/run_scheduler.py' || true"
timeout /t 2 >nul 2>&1
ssh -p !SERVER_PORT! -o LogLevel=ERROR -o StrictHostKeyChecking=no -i !SSH_KEY_ABS! !SERVER_USER!@!SERVER_IP! "pkill -9 -f 'backend/run_scheduler.py' || true"
timeout /t 2 >nul 2>&1
echo [OK]

echo [STEP 2] Upload files...
scp -P !SERVER_PORT! -o LogLevel=ERROR -o StrictHostKeyChecking=no -i !SSH_KEY_ABS! "%PROJECT_ROOT%\backend\run_scheduler.py" !SERVER_USER!@!SERVER_IP!:%REMOTE_PATH%/backend/run_scheduler.py
scp -P !SERVER_PORT! -o LogLevel=ERROR -o StrictHostKeyChecking=no -i !SSH_KEY_ABS! -r "%PROJECT_ROOT%\backend\config" !SERVER_USER!@!SERVER_IP!:%REMOTE_PATH%/backend/
echo [OK]

echo [STEP 3] Start scheduler...
start /b cmd /c "ssh -p !SERVER_PORT! -o LogLevel=ERROR -o StrictHostKeyChecking=no -i !SSH_KEY_ABS! !SERVER_USER!@!SERVER_IP! \"mkdir -p '!REMOTE_PATH!/logs/!TODAY!' ^&^& cd '!REMOTE_PATH!' ^&^& nohup python3 backend/run_scheduler.py >'!REMOTE_PATH!/logs/!TODAY!/scheduler.log' 2^>^&1 ^&^& exit""
echo [OK]

echo [STEP 4] Verify...
timeout /t 2 >nul 2>&1
ssh -p !SERVER_PORT! -o LogLevel=ERROR -o StrictHostKeyChecking=no -i !SSH_KEY_ABS! !SERVER_USER!@!SERVER_IP! "pgrep -f 'backend/run_scheduler.py' > /dev/null 2>&1 && echo '[OK] Running' || echo '[WARN] Not running'"

echo [STEP 5] Logs...
ssh -p !SERVER_PORT! -o LogLevel=ERROR -o StrictHostKeyChecking=no -i !SSH_KEY_ABS! !SERVER_USER!@!SERVER_IP! "head -10 '!REMOTE_PATH!/logs/!TODAY!/scheduler.log' 2>/dev/null || echo '(no log yet)'"

echo.
echo =================================================================
echo   Done
echo   Logs: tail -f !REMOTE_PATH!/logs/!TODAY!/scheduler.log
echo =================================================================
