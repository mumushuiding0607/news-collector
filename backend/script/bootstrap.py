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
from pathlib import Path

__all__ = ["APP_ROOT", "APP_ROOT_STR", "SCRIPT_DIR", "DB_PATH",
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
DB_PATH = Path(os.environ.get("NEWS_DB", str(APP_ROOT / "db" / "primary.db")))
LOG_DIR = APP_ROOT / "logs"
CACHE_DIR = APP_ROOT / "backend" / "cache"
CONFIG_DIR = APP_ROOT / "backend" / "config"
PROMPT_DIR = APP_ROOT / "backend" / "prompt"
SOURCES_CONFIG = CONFIG_DIR / "sources.json"


def init_bootstrap() -> None:
    """显式初始化：创建所有必要目录。供应用入口调用，不在模块 import 时自动执行。"""
    _ensure_dir(DB_PATH.parent)
    _ensure_dir(LOG_DIR)
    _ensure_dir(CACHE_DIR)
    _ensure_dir(CONFIG_DIR)