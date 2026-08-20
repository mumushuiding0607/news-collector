@echo off
setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%.."
set "DEPLOY_DIR=%SCRIPT_DIR%"
set "ENV_FILE=%DEPLOY_DIR%.env"

set "SERVER_IP=39.105.23.221"
set "SERVER_USER=root"
set "REMOTE_PATH=/opt/app"
set "SSH_KEY=./news_collector.pem"

echo.
echo ================================================================
echo   Step 0: Upload Changed Files
echo ================================================================

git -C "!PROJECT_ROOT!" diff --name-only -- backend/ > "%TEMP%\git_changes.txt"
git -C "!PROJECT_ROOT!" ls-files --others --exclude-standard -- backend/ >> "%TEMP%\git_changes.txt"

powershell -Command "(Get-Content '%TEMP%\git_changes.txt').Count" > "%TEMP%\git_count.txt"
set /p COUNT=<"%TEMP%\git_count.txt"
set "COUNT=!COUNT: =!"

echo COUNT after read is '[!COUNT!]'

if "!COUNT!"=="0" (
    echo [INFO] No changes in backend/
) else (
    echo [INFO] Found !COUNT! changed file(s):
    type "%TEMP%\git_changes.txt"
)
