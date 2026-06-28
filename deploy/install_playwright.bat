@echo off
REM ================================================================
REM Install Playwright on Remote Server
REM ================================================================
REM
REM Usage:
REM   1. Double-click to run, or run in cmd: install_playwright.bat
REM   2. Configuration is loaded from .env file in deploy directory
REM ================================================================

setlocal enabledelayedexpansion

REM ================================================================
REM Configuration
REM ================================================================
set "SCRIPT_DIR=%~dp0"
set "DEPLOY_DIR=%SCRIPT_DIR%"
set "ENV_FILE=%DEPLOY_DIR%.env"

REM Default values
set "SERVER_IP="
set "SERVER_USER=admin"
set "SERVER_PORT=22"
set "REMOTE_PATH=/opt/app"
set "SSH_KEY="

REM ================================================================
REM Load .env configuration
REM ================================================================
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
    echo [OK] Config loaded
    echo   SERVER_IP: !SERVER_IP!
    echo   SERVER_USER: !SERVER_USER!
    echo   REMOTE_PATH: !REMOTE_PATH!
) else (
    echo [ERROR] .env file not found
    exit /b 1
)

REM ================================================================
REM Build SSH command prefix
REM ================================================================
set "SSH_CMD=ssh"
if defined SSH_KEY (
    set "SSH_CMD=ssh -i !SSH_KEY!"
)
set "SSH_FULL=!SSH_CMD! -p %SERVER_PORT% -T %SERVER_USER%@%SERVER_IP%"

set CONFIRM=y

REM ================================================================
REM Install Playwright
REM ================================================================
echo.
echo ================================================================
echo   Installing Playwright Browsers
echo ================================================================
!SSH_FULL! "if [ ! -d '/root/.cache/ms-playwright' ]; then echo '[INFO] Installing Playwright browsers...' && cd '%REMOTE_PATH%' && python3 -m playwright install chromium; else echo '[SKIP] Playwright already installed'; fi"
echo [OK] Done
