$ErrorActionPreference = "SilentlyContinue"
$repo = "E:\Workspaces\MoltBot\news-collector"
$log = "$repo\logs\daily_pull.log"

function Write-Log {
    param($msg)
    "$((Get-Date).ToString('yyyy-MM-dd HH:mm:ss')) $msg" | Add-Content -Path $log -Encoding UTF8
}

Write-Log "=== 开始每日拉取 ==="

# 1. 终止占用 db 的 Python 进程
Get-Process | Where-Object { $_.Path -like "*python*" } | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 3
Write-Log "已终止 Python 进程"

# 2. 强制解锁 db 文件（删除锁标记）
$dbDir = "$repo\db"
Remove-Item -Path "$dbDir\primary.db-wal" -Force -ErrorAction SilentlyContinue
Remove-Item -Path "$dbDir\primary.db-shm" -Force -ErrorAction SilentlyContinue
Write-Log "已清理 db 锁文件"

# 3. 恢复 git 工作区（db目录）
Set-Location $repo
git checkout -- db/ 2>$null
Write-Log "已重置 db 目录"

# 4. 拉取远程
git fetch origin master 2>&1 | Add-Content -Path $log -Encoding UTF8
git pull origin master 2>&1 | Add-Content -Path $log -Encoding UTF8
Write-Log "===拉取完成 ==="