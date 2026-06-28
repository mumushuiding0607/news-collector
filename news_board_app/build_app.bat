@echo off
REM ================================================================
REM 风向标AI - Flutter APK 构建脚本
REM ================================================================
REM
REM 依赖项:
REM   - Flutter SDK
REM   - JDK17+ (C:\android-sdk\android-studio\jbr)
REM   - 签名密钥 (C:\android-sdk\news_board.jks)
REM   - signing.properties (android\app\signing.properties)
REM
REM 用法: 双击运行，或 cmd: build_app.bat
REM ================================================================

setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%"
set "JAVA_HOME=C:\android-sdk\android-studio\jbr"
set "FLUTTER_SDK=C:\Users\18145\dev\flutter_windows_3.44.0-stable\flutter"

echo ================================================================
echo   风向标AI - Flutter 构建脚本
echo ================================================================

REM ================================================================
REM 检查环境
REM ================================================================
echo [CHECK] 检查环境...
if not exist "%JAVA_HOME%\bin\java.exe" (
    echo [ERROR] JDK not found: %JAVA_HOME%\bin\java.exe
    pause
    exit /b 1
)
echo   [OK] JDK found

if not exist "%FLUTTER_SDK%\bin\flutter.bat" (
    echo [ERROR] Flutter SDK not found
    pause
    exit /b 1
)
echo   [OK] Flutter SDK found

REM ================================================================
REM 加载 publish/metadata.json（单一数据源）
REM ================================================================
echo.
echo [INFO] 读取 publish/metadata.json...

set "VERSION_NAME="
set "VERSION_CODE="

for /f "usebackq eol=# delims=," %%a in ("%PROJECT_ROOT%publish\metadata.json") do (
    echo %%a | findstr /C:"version_name" >nul2>&1
    if not errorlevel 1 (
        for /f "tokens=1,* delims=:" %%v in ("%%a") do set "VERSION_NAME=%%w"
    )
    echo %%a | findstr /C:"version_code" >nul 2>&1
    if not errorlevel 1 (
        for /f "tokens=1,* delims=:" %%v in ("%%a") do set "VERSION_CODE=%%w"
    )
)

set "VERSION_NAME=!VERSION_NAME: =!"
set "VERSION_CODE=!VERSION_CODE: =!"
set "VERSION_NAME=!VERSION_NAME:"=!"
set "VERSION_CODE=!VERSION_CODE:"=!"

echo   版本: !VERSION_CODE! (!VERSION_NAME!)

REM ================================================================
REM 设置环境变量
REM ================================================================
set "OLD_JAVA_HOME=%JAVA_HOME%"
set "PATH=%JAVA_HOME%\bin;%FLUTTER_SDK%\bin;%PATH%"

cd /d "%PROJECT_ROOT%"

REM ================================================================
REM 构建
REM ================================================================
echo.
echo [INFO] flutter clean...
call "%FLUTTER_SDK%\bin\flutter.bat" clean >nul 2>&1
echo   [OK] clean 完成

echo.
echo [INFO] flutter pub get...
call "%FLUTTER_SDK%\bin\flutter.bat" pub get 2>&1 | findstr /C:"Got dependencies"
echo   [OK] 依赖获取完成

echo.
echo [INFO] flutter build apk --release...
call "%FLUTTER_SDK%\bin\flutter.bat" build apk --release 2>&1

if errorlevel 1 (
    echo.
    echo [ERROR] APK 构建失败
    pause
    exit /b 1
)

REM ================================================================
REM 验证产物
REM ================================================================
set "APK_PATH=%PROJECT_ROOT%build\app\outputs\flutter-apk\app-release.apk"
if exist "!APK_PATH!" (
    for %%a in ("!APK_PATH!") do set "APK_SIZE=%%~za"
    set "APK_SIZE_MB=!APK_SIZE:~0,-3!"
    echo.
    echo   [OK] APK 构建完成
    echo   路径: !APK_PATH!
    echo   大小: !APK_SIZE_MB! KB
) else (
    echo [ERROR] APK 文件未找到
    pause
    exit /b 1
)

echo.
echo ================================================================
echo   构建完成
echo ================================================================
echo   APK: build\app\outputs\flutter-apk\app-release.apk
echo   版本: !VERSION_NAME! (versionCode !VERSION_CODE!)
echo ================================================================
pause