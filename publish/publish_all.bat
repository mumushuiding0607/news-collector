@echo off
REM ================================================================
REM News Board - One-click Build, Upload and Publish Script
REM ================================================================
REM
REM Steps:
REM   1. Build APK (flutter build apk --release)
REM   2. Upload APK to server /opt/backend/apk/
REM   3. Update backend/config.json version config
REM   4. Optional: Publish to Xiaomi/Huawei app store
REM
REM Preconditions:
REM   - publish/.env has all required config
REM   - Server backend/apk/ directory exists
REM   - SSH_KEY exists in deploy/ directory
REM
REM Usage: Double-click or cmd: publish_all.bat
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
echo   News Board - One-click Publish Script
echo ================================================================
echo   Version: !VERSION_NAME! (versionCode !VERSION_CODE!)
echo   Server: !SERVER_USER!@!SERVER_IP!:!SERVER_PORT!
echo ================================================================

REM ================================================================
REM Step 1: Build APK
REM ================================================================
echo.
echo [1/5] Building APK...
call "%SCRIPT_DIR%build_app.bat"
if errorlevel 1 (
    echo [ERROR] APK build failed
    exit /b 1
)
echo [OK] APK build complete

REM ================================================================
REM Step 2: Upload APK to server
REM ================================================================
echo.
echo [2/5] Uploading APK to server...
call "%SCRIPT_DIR%upload_apk.bat"
if errorlevel 1 (
    echo [WARN] APK upload failed, please check network
    exit /b 1
)
echo [OK] APK upload complete

REM ================================================================
REM Step 3: Update backend version config
REM ================================================================
echo.
echo [3/5] Updating backend version config...
call "%SCRIPT_DIR%update_version.bat"
if errorlevel 1 (
    echo [WARN] Version config update failed
    exit /b 1
)
echo [OK] Version config updated

REM ================================================================
REM Step 4: Publish to Xiaomi app store (optional)
REM ================================================================
echo.
echo [4/5] Checking Xiaomi app store...
if defined MI_APP_ID (
    call :publish_xiaomi
) else (
    echo [SKIP] Xiaomi credentials not configured
)

REM ================================================================
REM Step 5: Publish to Huawei app store (optional)
REM ================================================================
echo.
echo [5/5] Checking Huawei app store...
if defined HW_CLIENT_ID (
    call :publish_huawei
) else (
    echo [SKIP] Huawei credentials not configured
)

REM ================================================================
REM Complete
REM ================================================================
echo.
echo ================================================================
echo   One-click publish complete!
echo ================================================================
echo   Version: !VERSION_NAME! (build !VERSION_CODE!)
echo   APK:  http://!SERVER_IP!:!APP_PORT!/apk/news_board_!VERSION_NAME!.apk
echo.
echo   App store status:
echo     Xiaomi: !MI_STATUS!
echo     Huawei: !HW_STATUS!
echo ================================================================
exit /b 0

REM ================================================================
REM Publish to Xiaomi app store
REM ================================================================
:publish_xiaomi
set "MI_STATUS=not executed"
echo   [INFO] Publishing to Xiaomi...

set "MI_UPLOAD_URL=https://api.io.mi.com/openapi/developer/v2/app/upload"
set "APK_PATH=!PROJECT_ROOT!\build\app\outputs\flutter-apk\app-release.apk"

curl -X POST "!MI_UPLOAD_URL!" ^
  -H "Content-Type: multipart/form-data" ^
  -H "Authorization: Bearer !MI_ACCESS_TOKEN!" ^
  -F "file=@!APK_PATH!" ^
  -F "appId=!MI_APP_ID!" ^
  -F "appVersion=!VERSION_NAME!" ^
  -F "appVersionCode=!VERSION_CODE!" ^
  -F "buildType=release" ^
  -o "!TEMP!\_mi_resp.json" ^
  --max-time 300 ^
  -s

findstr /C:"success" /C:"10000" "!TEMP!\_mi_resp.json" >nul 2>&1
if errorlevel 1 (
    echo   [WARN] Xiaomi upload failed, check credentials
    set "MI_STATUS=failed"
) else (
    echo   [OK] APK uploaded to Xiaomi, please submit for review in dev console
    set "MI_STATUS=uploaded"
)
del "!TEMP!\_mi_resp.json"2>nul
exit /b 0

REM ================================================================
REM Publish to Huawei app store
REM ================================================================
:publish_huawei
set "HW_STATUS=not executed"
echo   [INFO] Publishing to Huawei...

REM Get Access Token
set "HW_TOKEN_URL=https://connect-api.cloud.huawei.com/api/oauth2/v1/token"
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
    echo   [WARN] Failed to get Huawei Token
    set "HW_STATUS=Token failed"
    del "!TEMP!\_hw_token.json" 2>nul
    exit /b 0
)

REM Upload APK
set "HW_UPLOAD_URL=https://connect-api.cloud.huawei.com/api/app/v2/upload/file"
set "APK_PATH=!PROJECT_ROOT!\build\app\outputs\flutter-apk\app-release.apk"
curl -X POST "!HW_UPLOAD_URL!" ^
  -H "Authorization: Bearer !HW_ACCESS_TOKEN!" ^
  -H "client_id: !HW_CLIENT_ID!" ^
  -F "file=@!APK_PATH!" ^
  -F "appId=!HW_APP_ID!" ^
  -o "!TEMP!\_hw_resp.json" ^
  --max-time 300 ^
  -s

findstr /C:"success" /C:"200" "!TEMP!\_hw_resp.json" >nul 2>&1
if errorlevel 1 (
    echo   [WARN] Huawei upload failed, check AppId
    set "HW_STATUS=failed"
) else (
    echo   [OK] APK uploaded to Huawei, please submit for review in dev console
    set "HW_STATUS=uploaded"
)

del "!TEMP!\_hw_token.json" 2>nul
del "!TEMP!\_hw_resp.json" 2>nul
exit /b 0
