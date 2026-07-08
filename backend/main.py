"""
main.py - 新闻看板 API 服务器
"""

from __future__ import annotations

import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

_BACKEND_DIR = Path(__file__).resolve().parent
for _p in (str(_BACKEND_DIR), str(_BACKEND_DIR.parent)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from backend.api import (
    admin_router,
    auth_router,
    comments_router,
    config_router,
    feedback_router,
    log_router,
    news_router,
    schedule_router,
    subscription_router,
)
from backend.api.config_api import get_app_config, update_app_config, get_app_version_config
from script.log import init_log, api_exception_handler, request_log_middleware
from script.bootstrap import init_bootstrap
from script.db import init_db

# ---------------------------------------------------------------------------
# 日志初始化（必须最早执行）
# ---------------------------------------------------------------------------

init_log()
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("[Startup] 初始化目录结构...")
    init_bootstrap()
    logger.info("[Startup] 检查并迁移数据库结构...")
    init_db()
    logger.info("[Startup] 数据库结构检查完成")
    yield


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="新闻看板 API",
    description="新闻采集系统后端 API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 请求日志中间件
app.middleware("http")(request_log_middleware)

# 全局异常处理
app.add_exception_handler(Exception, api_exception_handler)

app.include_router(admin_router, prefix="/api")
app.include_router(news_router, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(subscription_router, prefix="/api")
app.include_router(feedback_router, prefix="/api")
app.include_router(comments_router, prefix="/api")
app.include_router(config_router, prefix="/api")
app.include_router(log_router, prefix="/api")
app.include_router(schedule_router, prefix="/api")


@app.get("/api/config")
def get_config() -> dict:
    return get_app_config()


@app.post("/api/config")
def post_config(data: dict) -> dict:
    return update_app_config(data)


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "新闻看板 API", "version": "1.0.0"}


# Cached at module level — initialized once, reused on every health check
_app_version: str | None = None

def _get_version() -> str:
    global _app_version
    if _app_version is None:
        _app_version = get_app_version_config().get("latest_version", "1.0.0")
    return _app_version

@app.get("/api/health")
def health() -> dict[str, str]:
    from datetime import datetime
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return {"status": "ok", "time": now, "version": _get_version()}


@app.get("/privacy.html")
def privacy_policy():
    """服务于应用市场审核的隐私政策页面"""
    privacy_file = _BACKEND_DIR / "privacy.html"
    if not privacy_file.exists():
        raise HTTPException(status_code=404, detail="privacy policy not found")
    return FileResponse(privacy_file, media_type="text/html; charset=utf-8")


@app.get("/apk/{filename}")
def download_apk(filename: str):
    """提供 APK 文件下载"""
    apk_dir = _BACKEND_DIR / "apk"
    apk_file = apk_dir / filename
    if not apk_file.exists():
        raise HTTPException(status_code=404, detail="APK not found")
    return FileResponse(
        apk_file,
        media_type="application/vnd.android.package-archive",
        filename=filename,
    )


@app.get("/img/{filename}")
def download_img(filename: str):
    """提供图片文件下载"""
    img_dir = _BACKEND_DIR.parent / "img"
    img_file = img_dir / filename
    if not img_file.exists():
        raise HTTPException(status_code=404, detail="Image not found")

    # 根据文件扩展名确定 Content-Type
    import mimetypes
    content_type, _ = mimetypes.guess_type(str(img_file))
    if content_type is None:
        content_type = "application/octet-stream"

    return FileResponse(img_file, media_type=content_type)


if __name__ == "__main__":
    import psutil
    import uvicorn
    import time
    import socket
    from dotenv import load_dotenv

    # 加载 .env 配置
    _env_path = _BACKEND_DIR / ".env"
    if _env_path.exists():
        load_dotenv(_env_path)

    PORT = int(os.environ.get("APP_PORT", "31234"))
    HOST = os.environ.get("APP_HOST", "0.0.0.0")
    APP_VERSION = os.environ.get("APP_VERSION", "1.0.0")

    def is_port_in_use(port: int) -> bool:
        """通过尝试绑定检查端口是否被占用（更可靠）。"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind((HOST, port))
                return False
            except OSError:
                return True

    def kill_port_processes(port: int) -> bool:
        """终止所有占用指定端口的进程。"""
        import subprocess
        import re

        # 方法1：尝试用 psutil 找到进程
        found = False
        for conn in psutil.net_connections(kind="inet"):
            if conn.laddr.port == port and conn.status == "LISTENING":
                pid = conn.pid
                logger.warning(f"[Port] 端口 {port} 被占用，PID {pid}，正在终止...")
                try:
                    if sys.platform == "win32":
                        subprocess.run(f"taskkill /F /T /PID {pid}", shell=True)
                    else:
                        psutil.Process(pid).kill()
                    found = True
                except psutil.NoSuchProcess:
                    pass

        # 方法2：如果 psutil 没找到（权限不足），用 netstat + taskkill
        if not found:
            logger.warning(f"[Port] psutil 未找到占用进程，尝试 netstat...")
            try:
                result = subprocess.run(
                    f'netstat -ano | findstr :{port}',
                    shell=True, capture_output=True, text=True
                )
                for line in result.stdout.strip().split("\n"):
                    if "LISTENING" in line:
                        # 格式: TCP    0.0.0.0:31234    0.0.0.0:0    LISTENING    29052
                        # PID 是最后一列
                        parts = line.split()
                        if parts:
                            pid = parts[-1].strip()
                            logger.warning(f"[Port] netstat 发现 PID {pid}，尝试终止...")
                            subprocess.run(f"taskkill /F /T /PID {pid}", shell=True)
                            found = True
            except Exception as e:
                logger.error(f"[Port] netstat 方法失败: {e}")

        # 等待进程真正退出（最多 15 秒）
        for _ in range(30):
            time.sleep(0.5)
            if not is_port_in_use(port):
                logger.info(f"[Port] 端口 {port} 已释放")
                return True
        return not is_port_in_use(port)

    if is_port_in_use(PORT):
        logger.warning(f"[Port] 端口 {PORT} 已被占用，正在尝试释放...")
        if not kill_port_processes(PORT):
            logger.error(f"[Port] 端口 {PORT} 无法释放，启动失败")
            sys.exit(1)

    logger.info(f"[Start] 启动服务 {HOST}:{PORT}...")
    uvicorn.run("backend.main:app", host=HOST, port=PORT, reload=False)