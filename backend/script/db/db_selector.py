"""
db_selector.py - Universal database selection based on news_type

所有需要根据 news_type 判断数据库的地方，统一调用本模块。
禁止在业务代码中直接写 if/else 判断数据库路径。

支持两种调用方式：
1. ensure_db(news_type) - 设置 ContextVar（同步 API/CLI 场景）
2. news_type_to_db_path(news_type) - 直接获取路径（适合需要路径的场景）
"""
from pathlib import Path
from typing import Literal

# 路径推导：从本文件位置推断 APP_ROOT（避免循环导入 bootstrap）
# db_selector.py → script/db/ → backend/script/ → backend/ → 项目根目录
_DB_DIR = Path(__file__).resolve().parent          # .../backend/script/db
_SCRIPT_DIR = _DB_DIR.parent                        # .../backend/script
_BACKEND_DIR = _SCRIPT_DIR.parent                   # .../backend
_PROJECT_ROOT = _BACKEND_DIR.parent                 # .../news-collector
DB_DIR = _PROJECT_ROOT / "db"

# 类型别名
NewsType = Literal["ai", "stock", "AI新闻", "股市新闻"]


def news_type_to_db_path(news_type: str) -> Path:
    """
    将 news_type 转换为数据库文件路径。

    支持简写和全称：
      "ai" / "AI新闻"       → db/ai_news.db
      "stock" / "股市新闻"   → db/primary.db

    Args:
        news_type: "ai" | "stock" | "AI新闻" | "股市新闻"

    Returns:
        Path: 数据库文件路径
    """
    normalized = _normalize(news_type)
    if normalized == "AI新闻":
        return DB_DIR / "ai_news.db"
    return DB_DIR / "primary.db"


def is_ai_news(news_type: str) -> bool:
    """判断是否为 AI 新闻库。"""
    return _normalize(news_type) == "AI新闻"


def ensure_db(news_type: str) -> None:
    """
    确保当前 ContextVar 指向正确的数据库，并预热该数据库的连接池。

    内部逻辑：
    1. 规范化 news_type（支持简写和全称）
    2. 设置 ContextVar（set_news_type）
    3. 预热对应数据库的连接池（lazy 初始化）

    Args:
        news_type: "ai" | "stock" | "AI新闻" | "股市新闻"
    """
    normalized = _normalize(news_type)

    # 设置 ContextVar
    from script.bootstrap import set_news_type
    set_news_type(normalized)

    # 预热对应数据库的连接池
    from script.bootstrap import get_db_path
    from script.db.connection import _get_pool
    _get_pool(str(get_db_path()))


def _normalize(news_type: str) -> str:
    """
    规范化 news_type 为全称。

    "ai" / "AI新闻"  → "AI新闻"
    "stock" / "股市新闻" → "股市新闻"
    """
    if news_type in ("ai", "AI新闻"):
        return "AI新闻"
    return "股市新闻"
