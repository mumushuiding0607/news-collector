@echo off
REM ================================================================
REM Auto Update Backend Version Config
REM ================================================================
REM
REM Functions:
REM 1. Update latest_version and latest_build from metadata.json
REM 2. Update update_description from metadata.json
REM
REM Preconditions:
REM   - publish/.env configured with server connection info
REM   - Server backend/config.json is writable
REM ================================================================

setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"

REM ================================================================
REM Load .env configuration
REM ================================================================
set "ENV_FILE=%SCRIPT_DIR%.env"

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
)

if not defined SERVER_IP (
    echo [ERROR] SERVER_IP not configured in .env
    exit /b 1
)
if not defined SSH_KEY (
    echo [ERROR] SSH_KEY not configured in .env
    exit /b 1
)

REM ================================================================
REM Read version from metadata.json
REM ================================================================
for /f "delims=" %%v in ('python "%SCRIPT_DIR%util\get_version.py" version_name') do set "VERSION_NAME=%%v"
for /f "delims=" %%c in ('python "%SCRIPT_DIR%util\get_version.py" version_code') do set "VERSION_CODE=%%c"
for /f "delims=" %%d in ('python "%SCRIPT_DIR%util\get_version.py" update_description') do set "UPDATE_DESC=%%d"

echo [INFO] Version: !VERSION_NAME! (build !VERSION_CODE!)
echo [INFO] Update desc: !UPDATE_DESC!

REM ================================================================
REM Remote paths
REM ================================================================
set "REMOTE_CONFIG=!REMOTE_PATH!/backend/config.json"
set "LOCAL_CONFIG=!TEMP!\config_update_!RANDOM!.json"

REM ================================================================
REM Download remote config
REM ================================================================
echo [INFO] Downloading remote config...
scp -P !SERVER_PORT! -i "!SSH_KEY!" "!SERVER_USER!@!SERVER_IP!:!REMOTE_CONFIG!" "!LOCAL_CONFIG!"
if errorlevel 1 (
    echo [ERROR] Failed to fetch remote config
    exit /b 1
)
echo [OK] Downloaded

REM ================================================================
REM In-place update via standalone helper script
REM ================================================================
python "%SCRIPT_DIR%util\update_config_helper.py" "!LOCAL_CONFIG!" "!VERSION_NAME!" "!VERSION_CODE!" "!UPDATE_DESC!"
if errorlevel 1 (
    echo [ERROR] Config update failed
    del "!LOCAL_CONFIG!" 2>nul
    exit /b 1
)

REM ================================================================
REM Upload updated config
REM ================================================================
echo [INFO] Uploading updated config to server...
scp -P !SERVER_PORT! -i "!SSH_KEY!" "!LOCAL_CONFIG!" "!SERVER_USER!@!SERVER_IP!:!REMOTE_CONFIG!"
if errorlevel 1 (
    echo [ERROR] Config upload failed
    del "!LOCAL_CONFIG!" 2>nul
    exit /b 1
)

echo [OK] Version config updated
echo   latest_version: !VERSION_NAME!
echo   latest_build: !VERSION_CODE!
echo   update_description: !UPDATE_DESC!

del "!LOCAL_CONFIG!" 2>nul

exit /b 0
