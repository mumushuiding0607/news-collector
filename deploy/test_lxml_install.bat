@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

set "SERVER_IP=39.105.23.221"
set "SERVER_USER=root"
set "SERVER_PORT=22"
set "SSH_KEY=./aliyun_key"

set "SSH_FULL=ssh -p %SERVER_PORT% -i %SSH_KEY% -o LogLevel=ERROR %SERVER_USER%@%SERVER_IP%"

echo [INFO] Testing crawl4ai install (this will check lxml dependency)...
!SSH_FULL! "LC_ALL=C python3 -m pip install crawl4ai --no-deps -i https://pypi.tuna.tsinghua.edu.cn/simple/ --no-cache-dir --break-system-packages"
echo [DONE] Exit code: %ERRORLEVEL%
pause
