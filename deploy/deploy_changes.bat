@echo off
setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%.."
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
if not defined REMOTE_PATH set "REMOTE_PATH=/opt/app"

set "SSH_KEY_ABS="
if defined SSH_KEY (
    for /f "delims=" %%i in ('powershell -Command "[System.IO.Path]::GetFullPath('!PROJECT_ROOT!\!SSH_KEY!')"') do set "SSH_KEY_ABS=%%i"
)

set "SCP_CMD=scp"
if defined SSH_KEY_ABS set "SCP_CMD=scp -i !SSH_KEY_ABS!"
set "SCP_FULL=!SCP_CMD! -P !SERVER_PORT!"

echo.
echo ================================================================
echo   Incremental Deploy - backend/ git changes
echo ================================================================
echo   Server: !SERVER_USER!@!SERVER_IP!:!SERVER_PORT!
echo   Remote: !REMOTE_PATH!
echo ================================================================
echo.

set "TMP=%TEMP%\git_changes_!RANDOM!.txt"
git -C "!PROJECT_ROOT!" diff --name-only -- backend/ > "!TMP!"
git -C "!PROJECT_ROOT!" ls-files --others --exclude-standard -- backend/ >> "!TMP!"

set "COUNT=0"
for /f %%A in ('type "!TMP!" ^| find /c /v ""') do set "COUNT=%%A"

if "!COUNT!"=="0" (
    echo [INFO] No changes in backend/
    del "!TMP!" 2>nul
    exit /b 0
)

echo [INFO] Found !COUNT! changed file(s):
type "!TMP!"
echo.

for /f "delims=" %%F in ('type "!TMP!"') do (
    set "relpath=%%F"
    set "relpath=!relpath:\=/!"
    set "remotepath=!REMOTE_PATH!/!relpath!"

    echo   !relpath! --^> !remotepath!
    !SCP_FULL! "!PROJECT_ROOT!\%%F" "!SERVER_USER!@!SERVER_IP!:/!remotepath!"
)

echo.
echo [OK] Done

del "!TMP!" 2>nul
