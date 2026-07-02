@echo off
REM ================================================================
REM Upload APK to Server (Self-hosted distribution)
REM ================================================================
REM
REM Preconditions:
REM   - publish/.env has SERVER_IP, SERVER_USER, SERVER_PORT, SSH_KEY
REM   - Server backend/apk/ directory exists and is writable
REM ================================================================

setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%~dp0..\news_board_app"

call "%SCRIPT_DIR%util\load_env.bat"
if errorlevel 1 (
    echo [ERROR] Failed to load config
    exit /b 1
)

REM Read version from metadata.json
for /f "delims=" %%v in ('python "%SCRIPT_DIR%util\get_version.py" version_name') do set "VERSION_NAME=%%v"
for /f "delims=" %%c in ('python "%SCRIPT_DIR%util\get_version.py" version_code') do set "VERSION_CODE=%%c"

set "APK_SOURCE=%SCRIPT_DIR%apk\news_board_!VERSION_NAME!.apk"
set "REMOTE_PATH=/opt/app/backend/apk"
set "APK_FILENAME=news_board_!VERSION_NAME!.apk"

if not exist "!APK_SOURCE!" (
    echo [ERROR] APK not found: !APK_SOURCE!
    exit /b 1
)

REM ================================================================
REM Upload APK to server
REM ================================================================
echo [INFO] Uploading APK to server...
echo   Source: !APK_SOURCE!
echo   Dest: !SERVER_USER!@!SERVER_IP!:!REMOTE_PATH!/!APK_FILENAME!

REM Ensure remote dir exists (scp does not auto-create parent dirs)
bash -c "ssh -p !SERVER_PORT! -i '!SSH_KEY!' !SERVER_USER!@!SERVER_IP! 'mkdir -p !REMOTE_PATH!'"
if errorlevel 1 (
    echo [ERROR] Failed to create remote dir !REMOTE_PATH!
    exit /b 1
)

bash -c "scp -P !SERVER_PORT! -i '!SSH_KEY!' '!APK_SOURCE!' '!SERVER_USER!@!SERVER_IP!:!REMOTE_PATH!/!APK_FILENAME!'"
if errorlevel 1 (
    echo [ERROR] APK upload failed
    exit /b 1
)

REM ================================================================
REM Upload app_icon.png to server
REM ================================================================
set "ICON_SOURCE=%SCRIPT_DIR%app_icon.png"
set "ICON_FILENAME=app_icon.png"

if exist "!ICON_SOURCE!" (
    echo [INFO] Uploading app_icon.png to server...
    bash -c "scp -P !SERVER_PORT! -i '!SSH_KEY!' '!ICON_SOURCE!' '!SERVER_USER!@!SERVER_IP!:!REMOTE_PATH!/!ICON_FILENAME!'"
    if errorlevel 1 (
        echo [ERROR] app_icon.png upload failed
        exit /b 1
    )
    echo [OK] app_icon.png uploaded
) else (
    echo [WARN] app_icon.png not found, skipping upload
)

REM ================================================================
REM Upload backend/config.json to server
REM ================================================================
set "CONFIG_SOURCE=%SCRIPT_DIR%..\backend\config.json"

if exist "!CONFIG_SOURCE!" (
    echo [INFO] Uploading backend/config.json to server...
    bash -c "scp -P !SERVER_PORT! -i '!SSH_KEY!' '!CONFIG_SOURCE!' '!SERVER_USER!@!SERVER_IP!:/opt/app/backend/config.json'"
    if errorlevel 1 (
        echo [ERROR] config.json upload failed
        exit /b 1
    )
    echo [OK] config.json uploaded
) else (
    echo [WARN] backend/config.json not found, skipping upload
)

echo [OK] APK upload complete
exit /b 0
