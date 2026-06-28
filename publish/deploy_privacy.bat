@echo off
REM ================================================================
REM News Board - Privacy Policy Deployment Script
REM ================================================================
REM
REM Upload privacy.html to backend server
REM Auto-deploys without confirmation
REM
REM Usage: Double-click or cmd: deploy_privacy.bat
REM ================================================================

setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"

call "%SCRIPT_DIR%util\load_env.bat"
if errorlevel 1 (
    echo [ERROR] Failed to load config
    exit /b 1
)

echo ================================================================
echo   Privacy Policy Deployment
echo ================================================================
echo   Server: !SERVER_USER!@!SERVER_IP!:!SERVER_PORT!
echo   Remote Path: !REMOTE_PATH!
echo ================================================================

REM ================================================================
REM Build SSH/SCP command
REM ================================================================
if defined SSH_KEY (
    set "SSH_FULL=ssh -p !SERVER_PORT! -i !SSH_KEY! !SERVER_USER!@!SERVER_IP!"
    set "SCP_FULL=scp -P !SERVER_PORT! -i !SSH_KEY!"
) else (
    set "SSH_FULL=ssh -p !SERVER_PORT! !SERVER_USER!@!SERVER_IP!"
    set "SCP_FULL=scp -P !SERVER_PORT!"
)

REM ================================================================
REM Upload privacy.html
REM ================================================================
echo.
echo [INFO] Uploading privacy.html...

set "PRIVACY_SRC=%~dp0..\backend\privacy.html"
set "PRIVACY_DST=!SERVER_USER!@!SERVER_IP!:!REMOTE_PATH!/backend/privacy.html"

!SCP_FULL! "!PRIVACY_SRC!" "!PRIVACY_DST!" 2>nul
if errorlevel 1 (
    echo [ERROR] Upload failed
    exit /b 1
)
echo [OK] Upload complete

REM ================================================================
REM Verify
REM ================================================================
echo.
echo [INFO] Verifying privacy page...
!SSH_FULL! "curl -s --max-time 10 -o /dev/null -w '%%{http_code}' http://localhost:!APP_PORT!/privacy.html" > "!TEMP!\_pc.txt" 2>nul
set /p HTTP_CODE=<"!TEMP!\_pc.txt"
del "!TEMP!\_pc.txt"2>nul

if "!HTTP_CODE!"=="200" (
    echo [OK] HTTP 200 - Page accessible
) else (
    echo [WARN] HTTP !HTTP_CODE! - Please restart backend service
)

echo.
echo ================================================================
echo   Deployment Complete
echo ================================================================
echo   URL: http://!SERVER_IP!:!APP_PORT!/privacy.html
echo ================================================================
