@echo off
REM ================================================================
REM News Collector - Admin Frontend Deployment Script
REM ================================================================
REM
REM 构建并部署 admin 前端项目到远程服务器
REM
REM 依赖:
REM   - .env 中的服务器配置 (SERVER_IP, SERVER_USER, etc.)
REM   - admin/ 目录下有完整的 Node.js 项目
REM
REM Usage: 双击运行 或 cmd: deploy_admin.bat
REM ================================================================

setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%~dp0.."
set "ADMIN_DIR=%PROJECT_ROOT%\..\admin"

REM ================================================================
REM Server config (from .env)
REM ================================================================
set "SERVER_IP=39.105.23.221"
set "SERVER_USER=root"
set "SERVER_PORT=22"
set "REMOTE_PATH=/opt/app"
set "SSH_KEY_PATH=%PROJECT_ROOT%\news_collector.pem"
set "APP_PORT=31234"

REM Check if SSH_KEY exists
if exist "!SSH_KEY_PATH!" (
    set "SSH_KEY=!SSH_KEY_PATH!"
)

echo ================================================================
echo   Admin Frontend Deployment
echo ================================================================
echo   Server: !SERVER_USER!@!SERVER_IP!:!SERVER_PORT!
echo   Remote Path: !REMOTE_PATH!/admin
echo ================================================================

REM ================================================================
REM Step 1: 检查 admin 项目
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
REM Step 2: 构建项目
REM ================================================================
echo.
echo [2/3] Building admin project...

cd /d "!ADMIN_DIR!"
call npm run build 2>nul
if errorlevel 1 (
    echo [ERROR] Build failed
    exit /b 1
)
echo [OK] Build complete

REM ================================================================
REM Step 3: 部署到远程服务器
REM ================================================================
echo.
echo [3/3] Deploying to remote server...

REM Build SSH/SCP command
if defined SSH_KEY (
    set "SSH_CMD=ssh -p !SERVER_PORT! -i !SSH_KEY! !SERVER_USER!@!SERVER_IP!"
    set "SCP_FULL=scp -P !SERVER_PORT! -i !SSH_KEY!"
) else (
    set "SSH_CMD=ssh -p !SERVER_PORT! !SERVER_USER!@!SERVER_IP!"
    set "SCP_FULL=scp -P !SERVER_PORT!"
)

REM Upload build directory
set "BUILD_SRC=!ADMIN_DIR!\dist"
set "BUILD_DST=!SERVER_USER!@!SERVER_IP!:!REMOTE_PATH!/admin"

REM Check local build output exists
if not exist "!BUILD_SRC!" (
    echo [ERROR] Build output not found: !BUILD_SRC!
    echo [INFO] Please check your build process
    exit /b 1
)

REM Create remote directory if not exists
echo [INFO] Creating remote directory...
!SSH_CMD! "mkdir -p !REMOTE_PATH!/admin"

echo [INFO] Uploading build files...
!SCP_FULL! -r "!BUILD_SRC!" "!BUILD_DST!" 2>nul
if errorlevel 1 (
    echo [ERROR] Upload failed
    exit /b 1
)
echo [OK] Files uploaded

REM Restart PM2 service
echo.
echo [INFO] Restarting admin service...

REM Check and install PM2 if needed
!SSH_CMD! "command -v pm2 >/dev/null 2>&1 || npm install -g pm2"

REM Stop and delete existing service (ignore errors)
!SSH_CMD! "pm2 stop admin-web 2>/dev/null; pm2 delete admin-web 2>/dev/null; true"

REM Start new service
!SSH_CMD! "pm2 serve /opt/app/admin/dist --name admin-web --port 5173"

echo [OK] Service restarted

REM ================================================================
REM Step 5: 验证部署
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
