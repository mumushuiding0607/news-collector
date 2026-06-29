# News Collector - PowerShell Deployment Script
$OutputEncoding = [Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$ErrorActionPreference = "Continue"
$env:SSH_KEY = "C:/Users/18145/.openclaw/workspace/news-collector/deploy/aliyun"
$env:SERVER_IP = "39.105.23.221"
$env:SERVER_USER = "root"
$env:SERVER_PORT = "22"
$env:REMOTE_PATH = "/opt/app"

$SSH_KEY = "C:/Users/18145/.openclaw/workspace/news-collector/deploy/aliyun"
$SERVER_IP = "39.105.23.221"
$SERVER_USER = "root"
$SERVER_PORT = "22"
$REMOTE_PATH = "/opt/app"

function Invoke-SSH {
    param($cmd)
    ssh -i $SSH_KEY -o StrictHostKeyChecking=no -o LogLevel=ERROR -p $SERVER_PORT "$SERVER_USER@$SERVER_IP" $cmd 2>&1
}

function Invoke-SCP {
    param($local, $remote)
    scp -i $SSH_KEY -o StrictHostKeyChecking=no -o LogLevel=ERROR -P $SERVER_PORT "$local" "$SERVER_USER@$SERVER_IP`:$remote" 2>&1
}

Write-Host ""
Write-Host "================================================================"
Write-Host "  News Collector - Deployment Script (PowerShell)"
Write-Host "================================================================"

# Step 1: Create Remote Directory
Write-Host ""
Write-Host "================================================================"
Write-Host "  Step 1: Create Remote Directory"
Write-Host "================================================================"
Invoke-SSH "mkdir -p '$REMOTE_PATH'"
Write-Host "[OK] Directory created"

# Step 2: Check dependencies
Write-Host ""
Write-Host "================================================================"
Write-Host "  Step 2: Check Python Dependencies"
Write-Host "================================================================"
$result = Invoke-SSH "if [ -f '$REMOTE_PATH/requirements.txt' ]; then echo 'EXISTS'; else echo 'FIRST-DEPLOY'; fi"
if ($result -eq "FIRST-DEPLOY") {
    Write-Host "[INFO] First deployment - will install all dependencies"
    $PIP_ACTION = "FULL"
} else {
    Write-Host "[INFO] Existing deployment - incremental install"
    $PIP_ACTION = "INCREMENTAL"
}

# Step 3: Upload project files
Write-Host ""
Write-Host "================================================================"
Write-Host "  Step 3: Upload Project Files"
Write-Host "================================================================"

Write-Host "[INFO] Uploading .env..."
Invoke-SCP "C:/Users/18145/.openclaw/workspace/news-collector/backend/.env" "$REMOTE_PATH/backend/.env"

Write-Host "[INFO] Uploading requirements.txt..."
Invoke-SCP "C:/Users/18145/.openclaw/workspace/news-collector/backend/requirements.txt" "$REMOTE_PATH/requirements.txt"

Write-Host "[INFO] Uploading backend directory..."
& scp -i $SSH_KEY -o StrictHostKeyChecking=no -o LogLevel=ERROR -r -P $SERVER_PORT "C:/Users/18145/.openclaw/workspace/news-collector/backend" "$SERVER_USER@$SERVER_IP`:$REMOTE_PATH" 2>&1 | Out-Null

Write-Host "[OK] Upload complete"

# Step 4: Install Python dependencies
if ($PIP_ACTION -ne "SKIP") {
    Write-Host ""
    Write-Host "================================================================"
    Write-Host "  Step 4: Install Python Dependencies"
    Write-Host "================================================================"

    Write-Host "[INFO] Installing packages..."
    Invoke-SSH "cd '$REMOTE_PATH' && LC_ALL=C python3 -m pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/ --no-cache-dir --break-system-packages" | Out-Null

    Write-Host "[INFO] Installing crawl4ai..."
    Invoke-SSH "cd '$REMOTE_PATH' && LC_ALL=C python3 -m pip install crawl4ai --no-deps -i https://mirrors.aliyun.com/pypi/simple/ --no-cache-dir --break-system-packages" | Out-Null

    Write-Host "[OK] Dependencies installed"
}

# Step 4b: Playwright
Write-Host ""
Write-Host "================================================================"
Write-Host "  Step 4b: Install Playwright Browsers"
Write-Host "================================================================"
Invoke-SSH "if [ ! -d '/root/.cache/ms-playwright' ]; then cd '$REMOTE_PATH' && python3 -m playwright install chromium > /dev/null 2>&1; fi" | Out-Null
Write-Host "[OK] Playwright check complete"

# Step 5-7: Stop, Start and Health Check
Write-Host ""
Write-Host "================================================================"
Write-Host "  Step 5-7: Stop, Start and Health Check"
Write-Host "================================================================"
Write-Host "[INFO] Uploading remote deployment script..."
Invoke-SCP "C:/Users/18145/.openclaw/workspace/news-collector/deploy/_deploy_remote.py" "/tmp/_deploy_remote.py"

Write-Host "[INFO] Running remote deployment script..."
Invoke-SSH "REMOTE_PATH='$REMOTE_PATH' python3 /tmp/_deploy_remote.py deploy"

# Deployment complete
Write-Host ""
Write-Host "================================================================"
Write-Host "  Deployment Complete!"
Write-Host "================================================================"
Write-Host "  Access:     http://$SERVER_IP`:31234/api/health"
Write-Host "  Logs:       ssh $SERVER_USER@$SERVER_IP tail -f /var/log/news_collector.log"
Write-Host "  Stop:       ssh $SERVER_USER@$SERVER_IP pkill -f 'uvicorn backend.main:app'"
Write-Host "================================================================"