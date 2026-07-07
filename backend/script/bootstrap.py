"""
bootstrap.py - 统一路径管理

所有脚本开头必须引用此模块：
    from script.bootstrap import *
    from script.config import APP_ROOT, DB_PATH

功能：
  - 设置 APP_ROOT 环境变量（容器内为 /app，Windows 开发环境自动推断）
  - 管理 sys.path，确保 common/、config/、db/ 等模块可正确导入
  - 提供统一的路径常量

注意：
  - 容器内 APP_ROOT=/app
  - 本地开发时自动推断为项目根目录（backend/ 的 parent）

使用 Pydantic BaseModel 作为配置类，替代硬编码路径常量。
"""

import os
import sys
from contextvars import ContextVar
from pathlib import Path

__all__ = ["APP_ROOT", "APP_ROOT_STR", "SCRIPT_DIR", "get_db_path",
           "is_ai_news_db", "get_news_type", "set_news_type", "parse_db_arg",
           "LOG_DIR", "CACHE_DIR", "CONFIG_DIR", "PROMPT_DIR", "SOURCES_CONFIG",
           "init_bootstrap"]


def _infer_app_root() -> Path:
    """本地开发时自动推断 APP_ROOT。

    bootstrap.py 位于 backend/script/bootstrap.py
    - parent      = backend/script/
    - parent.parent = backend/
    - parent.parent.parent = 项目根目录

    容器内 APP_ROOT=/app（所有代码直接放在 /app/ 下）
    """
    return Path(__file__).resolve().parent.parent.parent


def _ensure_dir(path: Path) -> None:
    """按需创建目录（惰性创建，不每次调用 mkdir）。"""
    path.mkdir(parents=True, exist_ok=True)


# APP_ROOT 一次性设置，后续模块直接引用，不再重复操作 sys.path
APP_ROOT = Path(os.environ.get("APP_ROOT", _infer_app_root()))
APP_ROOT_STR = str(APP_ROOT)

# 确保 backend/script/ 目录在 sys.path（只在首次需要时去重）
SCRIPT_DIR = APP_ROOT_STR + "/backend/script"
for _p in (SCRIPT_DIR, APP_ROOT_STR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# 常用路径（统一基于 APP_ROOT）
LOG_DIR = APP_ROOT / "logs"
CACHE_DIR = APP_ROOT / "backend" / "cache"
CONFIG_DIR = APP_ROOT / "backend" / "config"
PROMPT_DIR = APP_ROOT / "backend" / "prompt"
SOURCES_CONFIG = CONFIG_DIR / "sources.json"


# 上下文隔离的线程/任务级变量（每个 async task/thread 独立副本）
_news_type_var: ContextVar[str] = ContextVar("news_type", default="股市新闻")


def get_db_path() -> Path:
    """返回当前数据库路径。

    优先级：ContextVar（CLI/FastAPI） > 环境变量（subprocess 场景）
    """
    # ContextVar 已设置（CLI/FastAPI 场景）
    ctx_type = _news_type_var.get()
    if ctx_type != "股市新闻":  # 非默认值，说明已设置
        return APP_ROOT / "db" / ("ai_news.db" if ctx_type == "AI新闻" else "primary.db")
    # 回退环境变量（subprocess 场景，通过 run_scheduler.py 的 os.environ 设置）
    env_type = os.environ.get("NEWS_TYPE", "股市新闻")
    return APP_ROOT / "db" / ("ai_news.db" if env_type == "AI新闻" else "primary.db")


def is_ai_news_db() -> bool:
    """判断当前是否使用 AI 新闻数据库。"""
    ctx_type = _news_type_var.get()
    if ctx_type != "股市新闻":
        return ctx_type == "AI新闻"
    return os.environ.get("NEWS_TYPE", "股市新闻") == "AI新闻"


def get_news_type() -> str:
    """返回当前新闻类型：股市新闻 或 AI新闻。"""
    return _news_type_var.get()


def set_news_type(news_type: str) -> None:
    """设置当前 context 的新闻类型。"""
    _news_type_var.set(news_type)


def parse_db_arg(argv: list[str]) -> list[str]:
    """从命令行参数中解析 --type 并设置新闻类型，返回清理后的 argv。

    用法：python xxx.py --type AI新闻
    """
    new_argv = []
    skip_next = False
    for arg in argv:
        if skip_next:
            skip_next = False
            continue
        if arg == "--type":
            skip_next = True
            continue
        new_argv.append(arg)
    if len(argv) > len(new_argv):
        for i, arg in enumerate(argv):
            if arg == "--type" and i + 1 < len(argv):
                set_news_type(argv[i + 1])
                break
    return new_argv


# 兼容旧代码（值可能不准确，取决于调用时机）
DB_PATH = APP_ROOT / "db" / "primary.db"


def init_bootstrap() -> None:
    """显式初始化：创建所有必要目录。供应用入口调用，不在模块 import 时自动执行。"""
    _ensure_dir(get_db_path().parent)
    _ensure_dir(LOG_DIR)
    _ensure_dir(CACHE_DIR)
    _ensure_dir(CONFIG_DIR)