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
echo   News Collector - Deployment Script
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
if defined SSH_KEY (
    set "SSH_KEY_FULL=!PROJECT_ROOT!\!SSH_KEY!"
    for /f "delims=" %%i in ('powershell -Command "[System.IO.Path]::GetFullPath('!SSH_KEY_FULL!')"') do set "SSH_KEY_ABS=%%i"
    if defined SSH_KEY_ABS (
        icacls "!SSH_KEY_ABS!" /inheritance:r /grant:r "!USERNAME!:R" >nul 2>&1
        mkdir "!USERPROFILE!\AppData\Local\Packages\Microsoft.WindowsTerminal_8wekyb3d8bbwe\LocalState\.ssh" >nul 2>&1
        copy /y "!SSH_KEY_ABS!" "!USERPROFILE%\.ssh\id_rsa" >nul 2>&1
        icacls "!USERPROFILE%\.ssh\id_rsa" /inheritance:r /grant:r "!USERNAME!:R" >nul 2>&1
    )
)

if not exist "%PROJECT_ROOT%\backend\requirements.txt" echo [ERROR] requirements.txt not found && exit /b 1
if not exist "%PROJECT_ROOT%\backend\main.py" echo [ERROR] main.py not found && exit /b 1
if not exist "%PROJECT_ROOT%\backend\script\db\__init__.py" echo [ERROR] script/db/__init__.py not found && exit /b 1
echo [OK] Files found

echo =================================================================
echo   Server: !SERVER_USER!@!SERVER_IP!:!SERVER_PORT!
echo   Path:   !REMOTE_PATH!
echo =================================================================
echo.

echo [STEP 1] Create remote dir...
powershell -Command "ssh -p !SERVER_PORT! -o StrictHostKeyChecking=no !SERVER_USER!@!SERVER_IP! 'mkdir -p \"!REMOTE_PATH!\"'"
echo [OK]

echo [STEP 2] Upload requirements.txt [SKIPPED]...
echo [SKIP]

echo [STEP 3] Install Python deps [SKIPPED]...
echo [SKIP]

echo [STEP 4] Upload project files [SKIPPED]...
echo [SKIP]

echo [STEP 4b] Stop old services...
powershell -Command "ssh -p !SERVER_PORT! -o StrictHostKeyChecking=no !SERVER_USER!@!SERVER_IP! 'pkill -f \"uvicorn backend.main:app\" 2>/dev/null || true; pkill -f \"backend/run_scheduler" 2>/dev/null || true'"
echo [OK]

echo [STEP 5] Start uvicorn backend...
powershell -Command "ssh -p !SERVER_PORT! -o StrictHostKeyChecking=no !SERVER_USER!@!SERVER_IP! 'mkdir -p \"!REMOTE_PATH!/logs/!TODAY!\" && cd \"!REMOTE_PATH!\" && nohup python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 31234 >\"!REMOTE_PATH!/logs/!TODAY!/global.log\" 2>&1 &'"
echo [OK]

echo [STEP 6] Health check...
timeout /t 8 >nul 2>&1
powershell -Command "ssh -p !SERVER_PORT! -o StrictHostKeyChecking=no !SERVER_USER!@!SERVER_IP! 'curl -s --max-time 10 http://localhost:31234/api/health && echo \"[OK] Backend running\" || echo \"[ERROR] Backend not responding\"'"
echo [OK]

echo [STEP 7] Start scheduler...
powershell -Command "ssh -p !SERVER_PORT! -o StrictHostKeyChecking=no !SERVER_USER!@!SERVER_IP! 'mkdir -p \"!REMOTE_PATH!/logs/!TODAY!\" && cd \"!REMOTE_PATH!\" && nohup python3 backend/run_scheduler.py >\"!REMOTE_PATH!/logs/!TODAY!/scheduler.log\" 2>&1 &'"
echo [OK]

echo.
echo =================================================================
echo   Done
echo   Logs: tail -f !REMOTE_PATH!/logs/!TODAY!/scheduler.log
echo =================================================================
