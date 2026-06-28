@echo off
REM ================================================================
REM News Board - Full Auto Build, Upload and App Store Publish
REM ================================================================
REM
REM Prerequisites:
REM   1. Xiaomi/Huawei dev console credentials for app store publishing
REM   2. Credentials configured in .env
REM   3. Ensure backend/main.py is running (privacy.html path configured)
REM
REM Usage: Double-click or cmd: publish.bat
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

echo ================================================================
echo   News Board - Auto Publish Script
echo ================================================================
echo   Version: !VERSION_NAME! (versionCode !VERSION_CODE!)
echo ================================================================
echo.

REM ================================================================
REM Step 1: Build APK
REM ================================================================
echo [1/4] Building APK...
call "%SCRIPT_DIR%build_app.bat"
if errorlevel 1 (
    echo [ERROR] APK build failed, aborting
    exit /b 1
)
echo [OK] APK built

REM ================================================================
REM Step 2: Publish to Xiaomi app store
REM ================================================================
echo.
echo [2/4] Publishing to Xiaomi app store...
if defined MI_APP_ID (
    call :publish_xiaomi
) else (
    echo [SKIP] Xiaomi credentials not configured
    echo [INFO] Set MI_APP_ID / MI_API_KEY / MI_ACCESS_TOKEN in .env
)

REM ================================================================
REM Step 3: Publish to Huawei app store
REM ================================================================
echo.
echo [3/4] Publishing to Huawei app store...
if defined HW_CLIENT_ID (
    call :publish_huawei
) else (
    echo [SKIP] Huawei credentials not configured
    echo [INFO] Set HW_APP_ID / HW_CLIENT_ID / HW_CLIENT_SECRET in .env
)

REM ================================================================
REM Step 4: Done
REM ================================================================
echo.
echo ================================================================
echo   Publish Complete
echo ================================================================
echo   APK: !PROJECT_ROOT!\build\app\outputs\flutter-apk\app-release.apk
echo.
echo   Current app store and backend status:
echo   Xiaomi: https://open.xiaomi.com
echo   Huawei: https://developer.huawei.com/consumer
echo ================================================================
exit /b 0

REM ================================================================
REM Publish to Xiaomi app store
REM ================================================================
:publish_xiaomi
echo   AppId: !MI_APP_ID!

set "MI_UPLOAD_URL=https://api.io.mi.com/openapi/developer/v2/app/upload"

echo [INFO] Uploading APK...
curl -X POST "!MI_UPLOAD_URL!" ^
  -H "Content-Type: multipart/form-data" ^
  -H "Authorization: Bearer !MI_ACCESS_TOKEN!" ^
  -F "file=@!PROJECT_ROOT!\build\app\outputs\flutter-apk\app-release.apk" ^
  -F "appId=!MI_APP_ID!" ^
  -F "appVersion=!VERSION_NAME!" ^
  -F "appVersionCode=!VERSION_CODE!" ^
  -F "buildType=release" ^
  -o "!TEMP!\_mi_resp.json" ^
  --max-time 300 ^
  -s

findstr /C:"success" /C:"10000" "!TEMP!\_mi_resp.json" >nul 2>&1
if errorlevel 1 (
    echo   [ERROR] Xiaomi upload failed
    type "!TEMP!\_mi_resp.json"2>nul | findstr /V "WARNING"
) else (
    echo   [OK] APK uploaded to Xiaomi, please submit for review in dev console
)
del "!TEMP!\_mi_resp.json"2>nul
exit /b 0

REM ================================================================
REM Publish to Huawei app store
REM ================================================================
:publish_huawei
echo   AppId: !HW_APP_ID!

REM Get Access Token
set "HW_TOKEN_URL=https://connect-api.cloud.huawei.com/api/oauth2/v1/token"
echo   [INFO] Getting Huawei Access Token...
curl -X POST "!HW_TOKEN_URL!" ^
  -H "Content-Type: application/json" ^
  -d "{\"client_id\":\"!HW_CLIENT_ID!\",\"client_secret\":\"!HW_CLIENT_SECRET!\",\"grant_type\":\"client_credentials\"}" ^
  -o "!TEMP!\_hw_token.json" ^
  --max-time 30 ^
  -s

set "HW_ACCESS_TOKEN="
for /f "usebackq tokens=*" %%t in (`findstr /C:"access_token" "!TEMP!\_hw_token.json"`) do (
    set "line=%%t"
    set "line=!line:*access_token:=!"
    set "line=!line:,=!"
    set "line=!line: =!"
    set "line=!line:\"=!"
    set "HW_ACCESS_TOKEN=!line!"
)

if not defined HW_ACCESS_TOKEN (
    echo   [ERROR] Failed to get Token
    del "!TEMP!\_hw_token.json" 2>nul
    exit /b 0
)
echo   [OK] Token obtained

REM Upload APK
set "HW_UPLOAD_URL=https://connect-api.cloud.huawei.com/api/app/v2/upload/file"
echo   [INFO] Uploading APK...
curl -X POST "!HW_UPLOAD_URL!" ^
  -H "Authorization: Bearer !HW_ACCESS_TOKEN!" ^
  -H "client_id: !HW_CLIENT_ID!" ^
  -F "file=@!PROJECT_ROOT!\build\app\outputs\flutter-apk\app-release.apk" ^
  -F "appId=!HW_APP_ID!" ^
  -o "!TEMP!\_hw_resp.json" ^
  --max-time 300 ^
  -s

findstr /C:"success" /C:"200" "!TEMP!\_hw_resp.json" >nul 2>&1
if errorlevel 1 (
    echo   [ERROR] Huawei upload failed
) else (
    echo   [OK] APK uploaded to Huawei, please submit for review in dev console
)

del "!TEMP!\_hw_token.json" 2>nul
del "!TEMP!\_hw_resp.json" 2>nul
exit /b 0
