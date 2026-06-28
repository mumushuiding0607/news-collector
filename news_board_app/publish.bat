@echo off
REM ================================================================
REM 风向标AI - 全自动构建并发布到小米/华为应用市场
REM ================================================================
REM
REM 前置条件:
REM   1. 在小米开放平台注册开发者账号并创建应用，获取 AppId + API Key
REM   2. 在华为 App Gallery Connect 注册并创建应用，获取 AppId + API Key
REM   3. 将凭证填入 publish_config.bat
REM   4. 首次发布前需先在后台手动上传一次 APK 完成应用创建
REM
REM 用法: 双击运行，或 cmd: publish.bat
REM ================================================================

setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%"
set "JAVA_HOME=C:\android-sdk\android-studio\jbr"
set "FLUTTER_SDK=C:\Users\18145\dev\flutter_windows_3.44.0-stable\flutter"
set "BACKEND_DIR=%SCRIPT_DIR%..\backend"

REM加载配置文件
if exist "%SCRIPT_DIR%publish_config.bat" (
    call "%SCRIPT_DIR%publish_config.bat"
) else (
    echo [ERROR] publish_config.bat 未找到，请先配置
    pause
    exit /b 1
)

REM 加载 .env 中的服务器配置
set "ENV_FILE=%~dp0..\publish\.env"
if exist "%ENV_FILE%" (
    for /f "eol=# delims=" %%a in ("%ENV_FILE%") do (
        set "line=%%a"
        set "line=!line:#=!"
        for /f "tokens=1,* delims==" %%k in ("!line!") do (
            set "key=%%k"
            set "val=%%~l"
            set "key=!key: =!"
            if not "!key!"=="" (
                set "!key!=!val!"
            )
        )
    )
)

REM ================================================================
REM 从 metadata.json 读取版本号
REM ================================================================
set "META_FILE=%SCRIPT_DIR%metadata.json"
set "VERSION_NAME="
set "VERSION_CODE="

for /f "usebackq tokens=*" %%t in (`findstr /C:"version_name" "%META_FILE%"`) do (
    set "line=%%t"
    for /f "tokens=1,* delims=:" %%a in ("!line!") do (
        set "val=%%b"
        set "val=!val:,=!"
        set "val=!val: =!"
        set "val=!val:"=!
        set "VERSION_NAME=!val!"
    )
)
for /f "usebackq tokens=*" %%t in (`findstr /C:"version_code" "%META_FILE%"`) do (
    set "line=%%t"
    for /f "tokens=1,* delims=:" %%a in ("!line!") do (
        set "val=%%b"
        set "val=!val:,=!"
        set "val=!val: =!
        set "val=!val:"=!
        set "VERSION_CODE=!val!"
    )
)

if not defined VERSION_NAME (
    echo [ERROR] 无法从 metadata.json 读取版本号
    pause
    exit /b 1
)

echo   版本: !VERSION_NAME! (build !VERSION_CODE!)

echo ================================================================
echo   风向标AI - 自动发布脚本
echo ================================================================
echo   版本: !VERSION_NAME! (versionCode !VERSION_CODE!)
echo ================================================================
echo.

REM ================================================================
REM Step 1: 构建 APK
REM ================================================================
echo [1/4] 构建 APK...
call "%SCRIPT_DIR%build_app.bat"
if errorlevel 1 (
    echo [ERROR] APK 构建失败，终止发布
    pause
    exit /b 1
)
echo [OK] APK 构建完成

REM ================================================================
REM Step 2: 发布到小米应用市场
REM ================================================================
echo.
echo [2/4] 发布到小米应用市场...
if defined MI_APP_ID (
    call :publish_xiaomi
) else (
    echo [SKIP] 未配置小米凭证，跳过
)

REM ================================================================
REM Step 3: 发布到华为应用市场
REM ================================================================
echo.
echo [3/4] 发布到华为应用市场...
if defined HW_CLIENT_ID (
    call :publish_huawei
) else (
    echo [SKIP] 未配置华为凭证，跳过
)

REM ================================================================
REM Step 4: 更新版本信息
REM ================================================================
echo.
echo [4/4] 更新版本信息...

REM 更新本地 backend/config.json
echo   [INFO] 更新本地 config.json...
python -c "
import json, sys
cfg_path = r'%BACKEND_DIR%\config.json'
with open(cfg_path, 'r', encoding='utf-8') as f:
    cfg = json.load(f)
if 'app_version' not in cfg:
    cfg['app_version'] = {}
cfg['app_version']['latest_version'] = '%VERSION_NAME%'
cfg['app_version']['latest_build'] = int('%VERSION_CODE%') if '%VERSION_CODE%' else 0
with open(cfg_path, 'w', encoding='utf-8') as f:
    json.dump(cfg, f, ensure_ascii=False, indent=2)
print('   [OK] 本地 config.json 已更新: !VERSION_NAME! (build !VERSION_CODE!)')
"
if errorlevel 1 (
    echo   [WARN] 本地 config.json 更新失败
)

REM 更新远程 backend/config.json（拉取 → 修改 → 上传）
set "REMOTE_CONFIG=/opt/app/backend/config.json"
set "TEMP_REMOTE_CFG=%TEMP%\_remote_cfg_!RANDOM!.json"

echo   [INFO] 拉取远程 config.json...
scp -P !SERVER_PORT! -i "!SSH_KEY!" "!SERVER_USER!@!SERVER_IP!:%REMOTE_CONFIG!" "!TEMP_REMOTE_CFG!" >nul 2>&1
if errorlevel 1 (
    echo   [WARN] 无法拉取远程 config.json，跳过远程更新
    goto :update_done
)

REM Python 修改远程配置
python -c "
import json, sys
with open(r'!TEMP_REMOTE_CFG!', 'r', encoding='utf-8') as f:
    cfg = json.load(f)
if 'app_version' not in cfg:
    cfg['app_version'] = {}
cfg['app_version']['latest_version'] = '%VERSION_NAME%'
cfg['app_version']['latest_build'] = int('%VERSION_CODE%') if '%VERSION_CODE%' else 0
with open(r'!TEMP_REMOTE_CFG!', 'w', encoding='utf-8') as f:
    json.dump(cfg, f, ensure_ascii=False, indent=2)
"
if errorlevel 1 (
    echo   [WARN] 远程 config.json 修改失败
    del "!TEMP_REMOTE_CFG!" 2>nul
    goto :update_done
)

echo   [INFO] 上传远程 config.json...
scp -P !SERVER_PORT! -i "!SSH_KEY!" "!TEMP_REMOTE_CFG!" "!SERVER_USER!@!SERVER_IP!:%REMOTE_CONFIG!" >nul 2>&1
if errorlevel 1 (
    echo   [WARN] 远程 config.json 上传失败
) else (
    echo   [OK] 远程 config.json 已更新
)
del "!TEMP_REMOTE_CFG!" 2>nul

:update_done

echo.
echo ================================================================
echo   发布流程完成
echo ================================================================
pause
exit /b 0

REM ================================================================
REM 发布到小米应用市场
REM ================================================================
:publish_xiaomi
echo AppId: !MI_APP_ID!

REM 获取上传凭证 (Mi App Store Open API)
echo [INFO] 请求上传凭证...
set "MI_UPLOAD_URL=https://api.io.mi.com/openapi/developer/v2/app/upload"

REM 上传 APK
curl -X POST "!MI_UPLOAD_URL!" ^
  -H "Content-Type: multipart/form-data" ^
  -H "Authorization: Bearer !MI_ACCESS_TOKEN!" ^
  -F "file=@build\app\outputs\flutter-apk\app-release.apk" ^
  -F "appId=!MI_APP_ID!" ^
  -F "appVersion=!VERSION_NAME!" ^
  -F "appVersionCode=!VERSION_CODE!" ^
  -F "buildType=release" ^
  -o "%TEMP%\_mi_resp.json" ^
  --max-time 300 ^
  -s

findstr /C:"success" "%TEMP%\_mi_resp.json" >nul 2>&1
if errorlevel 1 (
    echo   [ERROR] 小米上传失败，响应:
    type "%TEMP%\_mi_resp.json" | findstr /V "WARNING"
) else (
    echo   [OK] APK 已上传到小米应用市场，请前往后台提交审核
)
del "%TEMP%\_mi_resp.json" 2>nul
exit /b 0

REM ================================================================
REM 发布到华为应用市场
REM ================================================================
:publish_huawei
echo   AppId: !HW_APP_ID!

REM 获取 Access Token (AGC API)
echo   [INFO] 获取华为 Access Token...
set "HW_TOKEN_URL=https://connect-api.cloud.huawei.com/api/oauth2/v1/token"
curl -X POST "!HW_TOKEN_URL!" ^
  -H "Content-Type: application/json" ^
  -H "client_id: !HW_CLIENT_ID!" ^
  -d "{\"client_id\":\"!HW_CLIENT_ID!\",\"client_secret\":\"!HW_CLIENT_SECRET!\",\"grant_type\":\"client_credentials\"}" ^
  -o "%TEMP%\_hw_token.json" ^
  --max-time 30 ^
  -s

set "HW_ACCESS_TOKEN="
for /f "usebackq tokens=*" %%t in (`findstr /C:"access_token" "%TEMP%\_hw_token.json"`) do (
    set "line=%%t"
    set "line=!line:*access_token:=!"
    set "line=!line:,=!"
    set "line=!line: =!"
    set "line=!line:"=!"
    set "HW_ACCESS_TOKEN=!line!"
)
echo   Token: !HW_ACCESS_TOKEN!

REM 上传 APK
if defined HW_ACCESS_TOKEN (
    echo   [INFO] 上传 APK 到华为...
    set "HW_UPLOAD_URL=https://connect-api.cloud.huawei.com/api/app/v2/upload/file"
    curl -X POST "!HW_UPLOAD_URL!" ^
      -H "Authorization: Bearer !HW_ACCESS_TOKEN!" ^
      -H "client_id: !HW_CLIENT_ID!" ^
      -F "file=@build\app\outputs\flutter-apk\app-release.apk" ^
      -F "appId=!HW_APP_ID!" ^
      -o "%TEMP%\_hw_resp.json" ^
      --max-time 300 ^
      -s

    findstr /C:"success" /C:"200" "%TEMP%\_hw_resp.json" >nul 2>&1
    if errorlevel 1 (
        echo   [ERROR] 华为上传失败
    ) else (
        echo   [OK] APK 已上传到华为应用市场，请前往后台提交审核
    )
    del "%TEMP%\_hw_resp.json" 2>nul
)
del "%TEMP%\_hw_token.json" 2>nul
exit /b 0