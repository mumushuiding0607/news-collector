@echo off
REM ================================================================
REM 指南针AI - 隐私政策页面部署脚本
REM ================================================================
REM
REM 将 privacy.html 部署到后端服务器
REM 需要先完成 backend main.py 的部署（包含 /privacy.html 路由）
REM
REM 用法: 双击运行，或 cmd: deploy_privacy.bat
REM ================================================================

setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%"

REM 从 backend\.env 读取服务器配置
set "ENV_FILE=%PROJECT_ROOT%..\backend\.env"
set "SERVER_IP="
set "SERVER_USER=root"
set "SERVER_PORT=22"
set "REMOTE_PATH=/opt/backend"
set "SSH_KEY="

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
    echo [ERROR] SERVER_IP not found in %ENV_FILE%
    pause
    exit /b 1
)

set "SSH_CMD=ssh"
set "SCP_CMD=scp"
if defined SSH_KEY (
    set "SSH_CMD=ssh -i !SSH_KEY!"
    set "SCP_CMD=scp -i !SSH_KEY!"
)
set "SSH_FULL=!SSH_CMD! -p !SERVER_PORT! !SERVER_USER!@!SERVER_IP!"
set "SCP_FULL=!SCP_CMD! -P !SERVER_PORT!"

echo ================================================================
echo   隐私政策部署
echo ================================================================
echo   服务器: !SERVER_USER@!SERVER_IP!:!SERVER_PORT!
echo   路径:   !REMOTE_PATH!
echo ================================================================

set /p CONFIRM="确认部署 privacy.html? (y/n): "
if /i not "!CONFIRM!"=="y" (
    echo 已取消
    pause
    exit /b 0
)

REM 上传 privacy.html
echo.
echo [INFO] 上传 privacy.html...
!SCP_FULL! "%PROJECT_ROOT%..\backend\privacy.html" !SERVER_USER@!SERVER_IP!:%REMOTE_PATH%/backend/privacy.html

if errorlevel 1 (
    echo [ERROR] 上传失败
    pause
    exit /b 1
)
echo [OK] 上传完成

REM 验证
echo.
echo [INFO] 验证隐私政策页面...
!SSH_FULL! "curl -s --max-time 10 -o /dev/null -w '%{http_code}' http://localhost:31234/privacy.html" > "%TEMP%\_privacy_code.txt"
set /p HTTP_CODE=<"%TEMP%\_privacy_code.txt"
del "%TEMP%\_privacy_code.txt"

if "!HTTP_CODE!"=="200" (
    echo [OK] HTTP 200 - 页面可访问
) else (
    echo   [WARN] HTTP !HTTP_CODE! - 请检查服务器是否已重启
)

echo.
echo ================================================================
echo   部署完成
echo ================================================================
echo   访问: http://!SERVER_IP!:31234/privacy.html
echo ================================================================
pause
