@echo off
REM ================================================================
REM News Board - Flutter APK Build Script
REM ================================================================
REM
REM Prerequisites:
REM   - Flutter SDK
REM   - JDK17+ (JAVA_HOME in .env)
REM   - Signing key (ANDROID_SDK_KEYSTORE in .env)
REM   - signing.properties (news_board_app/android/app/signing.properties)
REM
REM Usage: Double-click or cmd: build_app.bat
REM ================================================================

setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%~dp0..\news_board_app"

REM ================================================================
REM Load .env config
REM ================================================================
call "%SCRIPT_DIR%util\load_env.bat"
if errorlevel 1 (
    echo [ERROR] Failed to load config
    exit /b 1
)

REM ================================================================
REM Auto-bump version_code and sync to backend/config.json latest_build
REM   - Set SKIP_BUMP=1 to skip (e.g. hotfix / same version retry build)
REM   - To bump only patch: python bump_version.py --skip-name
REM ================================================================
echo [BUMP] Bumping version_code...
python "%SCRIPT_DIR%util\bump_version.py"
if errorlevel 1 (
    echo [ERROR] Version bump failed
    exit /b 1
)

REM Read version from metadata.json
for /f "delims=" %%v in ('python "%SCRIPT_DIR%util\get_version.py" version_name') do set "VERSION_NAME=%%v"
for /f "delims=" %%c in ('python "%SCRIPT_DIR%util\get_version.py" version_code') do set "VERSION_CODE=%%c"

echo ================================================================
echo   News Board - Flutter Build Script
echo ================================================================
echo   Version: !VERSION_NAME! (versionCode !VERSION_CODE!)
echo ================================================================

REM ================================================================
REM Check environment
REM ================================================================
echo [CHECK] Checking environment...
if not exist "!JAVA_HOME!\bin\java.exe" (
    echo [ERROR] JDK not found: !JAVA_HOME!\bin\java.exe
    echo [INFO] Set JAVA_HOME in .env
    exit /b 1
)
echo   [OK] JDK found

if not exist "!FLUTTER_SDK!\bin\flutter.bat" (
    echo [ERROR] Flutter SDK not found: !FLUTTER_SDK!\bin\flutter.bat
    exit /b 1
)
echo   [OK] Flutter SDK found

REM ================================================================
REM Set PATH
REM ================================================================
set "PATH=!JAVA_HOME!\bin;!FLUTTER_SDK!\bin;%PATH%"

cd /d "!PROJECT_ROOT!"

REM ================================================================
REM Build
REM ================================================================
echo.
echo [INFO] flutter clean...
call "!FLUTTER_SDK!\bin\flutter.bat" clean >nul 2>&1
echo   [OK] clean done

echo.
echo [INFO] flutter pub get...
call "!FLUTTER_SDK!\bin\flutter.bat" pub get 2>&1 | findstr /C:"Got dependencies"
echo   [OK] dependencies ready

echo.
echo [INFO] flutter build apk --release...
call "!FLUTTER_SDK!\bin\flutter.bat" build apk --release 2>&1

if errorlevel 1 (
    echo.
    echo [ERROR] APK build failed
    exit /b 1
)

REM ================================================================
REM Verify output
REM ================================================================
set "APK_SRC=!PROJECT_ROOT!\build\app\outputs\flutter-apk\app-release.apk"
if exist "!APK_SRC!" (
    for %%a in ("!APK_SRC!") do set "APK_SIZE=%%~za"
    set "APK_SIZE_MB=!APK_SIZE:~0,-3!"
    echo.
    echo   [OK] APK built successfully
) else (
    echo [ERROR] APK file not found
    exit /b 1
)

REM ================================================================
REM Copy APK to publish/apk directory
REM ================================================================
echo.
echo [INFO] Copying APK to publish/apk...
if not exist "%SCRIPT_DIR%apk" mkdir "%SCRIPT_DIR%apk"
set "APK_DEST=%SCRIPT_DIR%apk\news_board_!VERSION_NAME!.apk"
copy /Y "!APK_SRC!" "!APK_DEST!" >nul
if errorlevel 1 (
    echo [ERROR] APK copy failed
    exit /b 1
)
echo   [OK] APK copied to !APK_DEST!

echo.
echo ================================================================
echo   Build Summary
echo ================================================================
echo   APK: !APK_DEST!
echo   Size: !APK_SIZE_MB! KB
echo   Version: !VERSION_NAME! (versionCode !VERSION_CODE!)
echo ================================================================

REM ================================================================
REM Step 5: Upload APK to server (self-hosted distribution)
REM ================================================================
echo.
call "%SCRIPT_DIR%upload_apk.bat"
if errorlevel 1 (
    echo [WARN] APK upload failed, please upload manually
) else (
    echo [OK] APK uploaded to server
)

REM ================================================================
REM Step 6: Auto-update backend version config
REM ================================================================
echo.
call "%SCRIPT_DIR%update_version.bat"
if errorlevel 1 (
    echo [WARN] Version config update failed, please update backend/config.json manually
) else (
    echo [OK] Version config updated
)
