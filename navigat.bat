@echo off
echo 正在重置 Navicat 试用信息...
echo.

REM 关闭正在运行的 Navicat 进程
taskkill /f /im navicat.exe

REM 删除注册表中的授权信息
reg delete "HKEY_CURRENT_USER\Software\PremiumSoft\NavicatPremium\Registration17XCS" /f
reg delete "HKEY_CURRENT_USER\Software\PremiumSoft\NavicatPremium\Update" /f

REM 删除可能记录试用信息的 CLSID 项（可选，可以用于深度清理）
set rp=HKEY_CURRENT_USER\Software\Classes\CLSID
for /f "tokens=*" %%a in ('reg query "%rp%"') do (
    for /f "tokens=*" %%l in ('reg query "%%a" /f "Info" /s /e ^|findstr /i "Info"') do (
        echo 正在删除: %%a
        reg delete %%a /f
    )
    for /f "tokens=*" %%l in ('reg query "%%a" /f "ShellFolder" /s /e ^|findstr /i "ShellFolder"') do (
        echo 正在删除: %%a
        reg delete %%a /f
    )
)

echo 重置完成！
REM 重新启动 Navicat（请确保路径正确）
REM 注意：请将下面这个路径替换成你电脑上 navicat.exe 的真实路径！
start "" "C:\Program Files\PremiumSoft\Navicat Premium 17\navicat.exe"

exit