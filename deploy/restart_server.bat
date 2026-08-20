@echo off
chcp 65001 >nul 2>&1
REM ================================================================
REM News Collector - Restart Service Script
REM ================================================================
REM
REM Restart uvicorn backend and scheduler on remote server
REM
REM Usage:
REM   1. Double-click to run, or run in cmd: restart_server.bat
REM   2. Uses config from .env file in deploy directory
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
set "SSH_KEY=news_collector.pem"
set "SERVER_PYTHON=python3"

REM ================================================================
REM Load .env configuration
REM ================================================================
echo.
echo ================================================================
echo   News Collector - Restart Service
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
            if "!key!"=="SSH_KEY" (
                if not "!val!"=="" set "SSH_KEY=!val!"
            )
        )
    )
    if defined SERVER_IP (
        echo [OK] Config loaded
        echo   SERVER_IP: !SERVER_IP!
        echo   SERVER_USER: !SERVER_USER!
        echo   REMOTE_PATH: !REMOTE_PATH!
        echo   SSH_KEY: !SSH_KEY!
    ) else (
        echo [ERROR] Config file is incomplete or missing .env
        exit /b 1
    )
) else (
    echo [ERROR] Config file not found: %ENV_FILE%
    exit /b 1
)

REM ================================================================
REM Build SSH/SCP command prefix
REM ================================================================
set "SSH_KEY_ABS="
if defined SSH_KEY (
    set "SSH_KEY_FULL=%PROJECT_ROOT%\%SSH_KEY%"
)
for /f "delims=" %%i in ('powershell -Command "[System.IO.Path]::GetFullPath('%SSH_KEY_FULL%')"') do set "SSH_KEY_ABS=%%i"
if defined SSH_KEY_ABS (
    icacls "!SSH_KEY_ABS!" /inheritance:r /grant:r "!USERNAME!:R" >nul 2>&1
)

set "SSH_CMD=ssh"
if defined SSH_KEY_ABS (
    set "SSH_CMD=ssh -i !SSH_KEY_ABS!"
)
set "SSH_FULL=!SSH_CMD! -p !SERVER_PORT! -o LogLevel=ERROR !SERVER_USER!@!SERVER_IP!"

set "TODAY=%DATE:~0,4%-%DATE:~5,2%-%DATE:~8,2%"
for /f "delims=" %%i in ('powershell -Command "Get-Date -Format 'yyyy-MM-dd'"') do set "TODAY=%%i"

REM ================================================================
REM Step 0: Upload git-changed files under backend/
REM ================================================================
@REM echo.
@REM echo ================================================================
@REM echo   Step 0: Upload Changed Files
@REM echo ================================================================

@REM git -C "!PROJECT_ROOT!" diff --name-only -- backend/ 2^>nul > "%TEMP%\git_changes.txt"
@REM git -C "!PROJECT_ROOT!" ls-files --others --exclude-standard -- backend/ 2^>nul >> "%TEMP%\git_changes.txt"

@REM for /f %%A in ('type "%TEMP%\git_changes.txt" ^| %SystemRoot%\System32\find.exe /c /v ""') do set "COUNT=%%A"

@REM if "!COUNT!"=="0" (
@REM     echo [INFO] No changes in backend/
@REM     del "%TEMP%\git_changes.txt" 2>nul
@REM ) else (
@REM     echo [INFO] Found !COUNT! changed file(s):
@REM     type "%TEMP%\git_changes.txt"
@REM     echo.
@REM     goto :upload_retry
@REM )
@REM goto :after_upload

@REM :upload_retry
@REM set "UPLOAD_FAIL=0"
@REM for /f "delims=" %%F in ('type "%TEMP%\git_changes.txt"') do (
@REM     set "relpath=%%F"
@REM     set "relpath=!relpath:\=/!"
@REM     echo   !relpath! --^> !REMOTE_PATH!/!relpath!
@REM     scp -i "!SSH_KEY_ABS!" -P !SERVER_PORT! "!PROJECT_ROOT!\%%F" "!SERVER_USER!@!SERVER_IP!:/!REMOTE_PATH!/!relpath!"
@REM     if errorlevel 1 set "UPLOAD_FAIL=1"
@REM )
@REM if "!UPLOAD_FAIL!"=="1" (
@REM     echo [%TIME%] Upload failed, retrying in 2 minutes...
@REM     timeout /t 120 /nobreak >nul
@REM     goto :upload_retry
@REM )
@REM echo [OK] Uploaded !COUNT! file(s)
@REM del "%TEMP%\git_changes.txt" 2>nul

@REM :after_upload

REM ================================================================
REM Step 1: Stop old main.py
REM ================================================================
echo.
echo ================================================================
echo   Step 1: Stop Backend
echo ================================================================
!SSH_FULL! "pkill -9 -f 'uvicorn.*backend.main' 2>/dev/null || true; echo 'main.py stopped'"
echo [OK] main.py stopped

echo.
echo ================================================================
echo   Step 2: Start Backend
echo ================================================================
start /b "" !SSH_FULL! "bash -c 'cd ''%REMOTE_PATH%'' && nohup python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 31234 > /dev/null 2>&1 &'"
echo 启动成功
timeout /t 1 /nobreak >nul
!SSH_FULL! "sleep 3 && curl -s --max-time 5 http://localhost:31234/api/health && echo '[OK] main.py is running' || echo '[ERROR] main.py not responding'"
echo [OK] main.py started

echo.
echo ================================================================
echo   Step 3: Stop Scheduler
echo ================================================================
!SSH_FULL! "pkill -9 -f 'run_scheduler' 2>/dev/null || true; echo 'run_scheduler stopped'"
echo [OK] run_scheduler stopped

echo.
echo ================================================================
echo   Step 4: Start Scheduler
echo ================================================================
start /b "" !SSH_FULL! "bash -c 'cd ''%REMOTE_PATH%'' && nohup python3 backend/run_scheduler.py >> ''%REMOTE_PATH%/logs/%TODAY%/scheduler.log'' 2>&1 &'"
echo [OK] run_scheduler started

REM ================================================================
REM Step 5: Health Check
REM ================================================================
echo.
echo ================================================================
echo   Step 5: Health Check
echo ================================================================
!SSH_FULL! "sleep 5 && curl -s --max-time 10 http://localhost:31234/api/health && echo '[OK] Backend is running' || echo '[ERROR] Backend not responding'"

echo.
echo ================================================================
echo   Log Output
echo ================================================================
echo --- Global Log (last 5 lines) ---
for /f "tokens=*" %%a in ('!SSH_FULL! "tail -5 '%REMOTE_PATH%/logs/%TODAY%/global.log' 2>/dev/null || echo '(no log yet)'" 2^>nul') do echo %%a
echo.
echo --- Scheduler Log (last 10 lines) ---
for /f "tokens=*" %%a in ('!SSH_FULL! "tail -10 '%REMOTE_PATH%/logs/%TODAY%/scheduler.log' 2>/dev/null || echo '(no scheduler log yet)'" 2^>nul') do echo %%a

REM ================================================================
REM Complete
REM ================================================================
echo.
echo ================================================================
echo   Restart Complete!
echo ================================================================
echo   Access:   http://!SERVER_IP!:31234/api/health
echo ================================================================
