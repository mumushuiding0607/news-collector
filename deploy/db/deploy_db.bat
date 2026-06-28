@echo off
REM ================================================================
REM Deploy DB to Remote Server
REM ================================================================
REM Push news-collector/db contents to remote opt/app/db/
REM Retries every 60 seconds until successful
REM ================================================================

setlocal enabledelayedexpansion

REM ================================================================
REM Path setup
REM ================================================================
set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

pushd "%SCRIPT_DIR%\..\.."
set "PROJECT_ROOT=%CD%"
popd

pushd "%SCRIPT_DIR%\.."
set "DEPLOY_DIR=%CD%"
popd

set "DB_DIR=%PROJECT_ROOT%\db"
set "REMOTE_PATH=/opt/app/db"
set "ENV_FILE=%DEPLOY_DIR%\.env"

REM ================================================================
REM Load .env (skip REMOTE_PATH)
REM ================================================================
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
            if "!key!"=="SSH_KEY" set "SSH_KEY=!val!"
        )
    )
)

if not defined SERVER_IP (
    echo [ERROR] SERVER_IP not configured in %ENV_FILE%
    exit /b 1
)

REM ================================================================
REM Convert SSH_KEY to absolute path if relative
REM ================================================================
if defined SSH_KEY (
    set "second_char=!SSH_KEY:~1,1!"
    if not "!second_char!"==":" (
        if not "!SSH_KEY:~0,1!"=="/" (
            set "SSH_KEY=%DEPLOY_DIR%\!SSH_KEY!"
        )
    )
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
set "SSH_FULL=!SSH_CMD! -p !SERVER_PORT! -T !SERVER_USER!@!SERVER_IP!"
set "SCP_FULL=!SCP_CMD! -P !SERVER_PORT!"

REM ================================================================
REM Loop until success
REM ================================================================
echo.
echo ================================================================
echo   DB Deployment Script
echo ================================================================
echo   Source:   %DB_DIR%
echo   Target:   %SERVER_USER%@%SERVER_IP%:%REMOTE_PATH%
echo   Mode:     Retry every 60 seconds until success
echo ================================================================

:retry
echo.
echo [%TIME%] Connecting to %SERVER_IP%...

REM Create remote db directory
!SSH_FULL! "mkdir -p '%REMOTE_PATH%'" 2>nul

REM Upload db files (overwrite)
echo [%TIME%] Uploading db files...
!SCP_FULL! -r "%DB_DIR%\*" "%SERVER_USER%@%SERVER_IP%:%REMOTE_PATH%/"

if errorlevel 1 (
    echo [%TIME%] Upload failed, retrying in 60 seconds...
    timeout /t60 /nobreak >nul
    goto :retry
)

echo.
echo ================================================================
echo   Deployment Complete!
echo ================================================================
echo   Remote: %SERVER_USER%@%SERVER_IP%:%REMOTE_PATH%
echo   Time:   %DATE% %TIME%
echo ================================================================
exit /b 0