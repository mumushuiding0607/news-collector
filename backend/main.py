"""
News Board API Server - FastAPI
"""
import sys
from pathlib import Path

# 项目根目录：C:\Users\18145\.openclaw\workspace\新闻采集
BASE_DIR = Path(__file__).resolve().parent.parent
# script/common 在 script/ 下，不在根目录，所以 common 路径要单独加
SCRIPT_DIR = BASE_DIR / "script"
sys.path.insert(0, str(BASE_DIR))   # backend.api, backend.core, backend.models 等
sys.path.insert(0, str(SCRIPT_DIR)) # common 等

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.api import news_router, rag_router, auth_router, subscription_router, feedback_router
from backend.api.config_api import get_app_config, update_app_config

app = FastAPI(
    title="新闻看板 API",
    description="新闻采集系统后端 API",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Router
app.include_router(news_router, prefix="/api")
app.include_router(rag_router, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(subscription_router, prefix="/api")
app.include_router(feedback_router, prefix="/api")
from backend.api.feedback import comments_router
app.include_router(comments_router, prefix="/api")


@app.get("/api/config")
def get_config():
    return get_app_config()


@app.post("/api/config")
def post_config(data: dict):
    return update_app_config(data)


@app.get("/")
def root():
    return {"message": "新闻看板 API", "version": "1.0.0"}


@app.get("/api/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",   # 支持 --reload 监控
        host="0.0.0.0",
        port=3000,
        reload=True,           # 代码改动自动重启
    )
