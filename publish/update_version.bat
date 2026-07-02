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

call "%SCRIPT_DIR%util\load_env.bat"
if errorlevel 1 (
    echo [ERROR] Failed to load config
    exit /b 1
)

REM Read version from metadata.json
for /f "delims=" %%v in ('python "%SCRIPT_DIR%util\get_version.py" version_name') do set "VERSION_NAME=%%v"
for /f "delims=" %%c in ('python "%SCRIPT_DIR%util\get_version.py" version_code') do set "VERSION_CODE=%%c"
for /f "delims=" %%d in ('python "%SCRIPT_DIR%util\get_version.py" update_description') do set "UPDATE_DESC=%%d"

echo [INFO] Version: !VERSION_NAME! (build !VERSION_CODE!)
echo [INFO] Update desc: !UPDATE_DESC!

REM ================================================================
REM Remote paths
REM ================================================================
set "REMOTE_CONFIG=/opt/app/backend/config.json"
set "LOCAL_CONFIG=/tmp/config_update_!RANDOM!.json"

REM ================================================================
REM Download remote config
REM ================================================================
echo [INFO] Downloading remote config...
bash -c "scp -P !SERVER_PORT! -i '!SSH_KEY!' '!SERVER_USER!@!SERVER_IP!:!REMOTE_CONFIG!' '!LOCAL_CONFIG!'"
if errorlevel 1 (
    echo [ERROR] Failed to fetch remote config
    exit /b 1
)
echo [OK] Downloaded

REM ================================================================
REM In-place update via standalone helper script
REM Using a separate .py script because cmd heredoc (.. echo ...) breaks
REM on parentheses in strings, causing parse errors in the python script
REM that then fail at runtime. The .py helper avoids cmd string parsing.
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
bash -c "scp -P !SERVER_PORT! -i '!SSH_KEY!' '!LOCAL_CONFIG!' '!SERVER_USER!@!SERVER_IP!:!REMOTE_CONFIG!'"
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
