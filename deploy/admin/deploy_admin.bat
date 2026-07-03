@echo off
REM ================================================================
REM News Collector - Admin Frontend Deployment Script
REM ================================================================
REM
REM Build and deploy admin frontend project to remote server
REM
REM Dependencies:
REM   - Server config in .env (SERVER_IP, SERVER_USER, etc.)
REM   - admin/ directory contains complete Node.js project
REM
REM Usage: Double-click to run or cmd: deploy_admin.bat
REM ================================================================

setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
for %%i in ("%~dp0..\..") do set "PROJECT_ROOT=%%~fi"
set "ADMIN_DIR=%PROJECT_ROOT%\admin"
set "ENV_FILE=%PROJECT_ROOT%\deploy\.env"

REM ================================================================
REM Load config from .env file
REM ================================================================
if exist "!ENV_FILE!" (
    for /f "usebackq tokens=1,* delims==" %%a in ("!ENV_FILE!") do (
        set "%%a=%%b"
    )
)

REM ================================================================
REM SSH key path - resolve relative path and fix permissions
REM ================================================================
if defined SSH_KEY (
    set "SSH_KEY_FULL=!PROJECT_ROOT!\!SSH_KEY!"
)
goto :after_keypath
:convert_keypath
for /f "delims=" %%i in ('powershell -Command "[System.IO.Path]::GetFullPath('%~1')"') do set "SSH_KEY_ABS=%%i"
exit /b 0
:after_keypath
if defined SSH_KEY (
    call :convert_keypath "!SSH_KEY_FULL!"
    if defined SSH_KEY_ABS (
        icacls "!SSH_KEY_ABS!" /inheritance:r /grant:r "!USERNAME!:R" >nul 2>&1
    )
)

echo ================================================================
echo   Admin Frontend Deployment
echo ================================================================
echo   Server: !SERVER_USER!@!SERVER_IP!:!SERVER_PORT!
echo   Remote Path: !REMOTE_PATH!/admin
if defined SSH_KEY_ABS echo   SSH Key: !SSH_KEY_ABS!
echo ================================================================

REM ================================================================
REM Step 1: Check admin project
REM ================================================================
echo.
echo [1/3] Checking admin project...

if not exist "!ADMIN_DIR!\package.json" (
    echo [ERROR] package.json not found in admin directory
    echo [INFO] Please ensure admin project exists at: !ADMIN_DIR!
    exit /b 1
)
echo [OK] package.json found

REM ================================================================
REM Step 2: Build project
REM ================================================================
echo.
echo [2/3] Building admin project...

REM Check if npm is available
where npm >nul 2>&1
if errorlevel 1 (
    echo [ERROR] npm not found. Please install Node.js and npm first.
    echo [INFO] Download from: https://nodejs.org/
    exit /b 1
)

cd /d "!ADMIN_DIR!"
call npm run build 2>nul
if errorlevel 1 (
    echo [ERROR] Build failed
    exit /b 1
)
echo [OK] Build complete

REM ================================================================
REM Step 3: Deploy to remote server
REM ================================================================
echo.
echo [3/3] Deploying to remote server...

REM Check local build output exists
if not exist "!ADMIN_DIR!\dist" (
    echo [ERROR] Build output not found: !ADMIN_DIR!\dist
    echo [INFO] Please check your build process
    exit /b 1
)

REM Create remote directory (clean)
echo [INFO] Cleaning remote directory...
if defined SSH_KEY_ABS (
    "E:\Git\usr\bin\ssh.exe" -p !SERVER_PORT! -i '!SSH_KEY_ABS!' !SERVER_USER!@!SERVER_IP! "rm -rf !REMOTE_PATH!/admin/*"
) else (
    "E:\Git\usr\bin\ssh.exe" -p !SERVER_PORT! !SERVER_USER!@!SERVER_IP! "rm -rf !REMOTE_PATH!/admin/*"
)

REM Upload build files
echo [INFO] Uploading build files...
if defined SSH_KEY_ABS (
    "E:\Git\usr\bin\scp.exe" -P !SERVER_PORT! -i '!SSH_KEY_ABS!' -r '!ADMIN_DIR!\dist'/* !SERVER_USER!@!SERVER_IP!:!REMOTE_PATH!/admin/
) else (
    "E:\Git\usr\bin\scp.exe" -P !SERVER_PORT! -r '!ADMIN_DIR!\dist'/* !SERVER_USER!@!SERVER_IP!:!REMOTE_PATH!/admin/
)
if errorlevel 1 (
    echo [ERROR] Upload failed
    exit /b 1
)
echo [OK] Files uploaded

REM Restart PM2 service
echo.
echo [INFO] Checking remote Node.js environment...

REM Check if npm is available on remote server
"E:\Git\usr\bin\ssh.exe" -p !SERVER_PORT! -i '!SSH_KEY_ABS!' !SERVER_USER!@!SERVER_IP! "command -v npm"
if errorlevel 1 (
    echo [WARN] npm not found on remote server, attempting to install Node.js...
    "E:\Git\usr\bin\ssh.exe" -p !SERVER_PORT! -i '!SSH_KEY_ABS!' !SERVER_USER!@!SERVER_IP! "curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && apt-get install -y nodejs"
    if errorlevel 1 (
        echo [ERROR] Node.js installation failed. Please install Node.js on the server manually.
        exit /b 1
    )
    echo [OK] Node.js installed
) else (
    echo [OK] Remote npm found
)

REM Check and install PM2 if needed
"E:\Git\usr\bin\ssh.exe" -p !SERVER_PORT! -i '!SSH_KEY_ABS!' !SERVER_USER!@!SERVER_IP! "command -v pm2 || npm install -g pm2"
if errorlevel 1 (
    echo [ERROR] PM2 installation failed
    exit /b 1
)
echo [OK] PM2 ready

REM Stop and delete existing service (ignore errors)
"E:\Git\usr\bin\ssh.exe" -p !SERVER_PORT! -i '!SSH_KEY_ABS!' !SERVER_USER!@!SERVER_IP! "pm2 stop admin-web 2>/dev/null; pm2 delete admin-web 2>/dev/null; true"

REM Start new service (SPA mode for Vue router)
"E:\Git\usr\bin\ssh.exe" -p !SERVER_PORT! -i '!SSH_KEY_ABS!' !SERVER_USER!@!SERVER_IP! "pm2 serve !REMOTE_PATH!/admin --name admin-web --port 5173 --spa"
echo [OK] Service restarted

REM ================================================================
REM Step 4: Verify deployment
REM ================================================================
echo.
echo [INFO] Verifying deployment...

for /f "delims=" %%c in ('curl -s --max-time 10 -w "%%{http_code}" -o "!TEMP!\_verify.txt" "http://!SERVER_IP!:5173" 2^nul') do set "HTTP_CODE=%%c"
if "!HTTP_CODE!"=="200" (
    echo [OK] HTTP 200 - Deployment successful
    del "!TEMP!\_verify.txt" 2>nul
) else (
    echo [WARN] HTTP !HTTP_CODE! - Please check manually
    if exist "!TEMP!\_verify.txt" (
        type "!TEMP!\_verify.txt" 2>nul | findstr /V "WARNING"
        del "!TEMP!\_verify.txt" 2>nul
    )
)

REM ================================================================
REM Done
REM ================================================================
echo.
echo ================================================================
echo   Deployment Complete
echo ================================================================
echo   URL: http://!SERVER_IP!:5173
echo ================================================================
