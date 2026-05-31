"""
config.py - 配置管理

集中管理项目配置，从环境变量和配置文件加载。
"""

import os
import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# 项目根目录
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


# ---------------------------------------------------------------------------
# 环境变量
# ---------------------------------------------------------------------------

_DOTENV_PATH = _PROJECT_ROOT / ".env"


def load_env():
    if _DOTENV_PATH.exists():
        import dotenv
        dotenv.load_dotenv(_DOTENV_PATH)


load_env()


# ---------------------------------------------------------------------------
# LLM 配置
# ---------------------------------------------------------------------------

LLM_API_KEY = os.environ.get("MINIMAX_API_KEY", "")
LLM_BASE_URL = os.environ.get("MINIMAX_BASE_URL", "https://api.minimaxi.com/anthropic")
LLM_MODEL = os.environ.get("MINIMAX_MODEL", "MiniMax-M2.7")


# ---------------------------------------------------------------------------
# 数据库
# ---------------------------------------------------------------------------

DB_PATH = _PROJECT_ROOT / "db" / "primary.db"


# ---------------------------------------------------------------------------
# 缓存
# ---------------------------------------------------------------------------

CACHE_DIR = _PROJECT_ROOT / "backend" / "cache"
LATEST_CACHE = CACHE_DIR / "news_latest.json"
HISTORY_CACHE = CACHE_DIR / "news_history.json"
HOT_CACHE = CACHE_DIR / "news_hot.json"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# sources.json
# ---------------------------------------------------------------------------

SOURCES_CONFIG = _PROJECT_ROOT / "config" / "sources.json"


def load_json_config(path: Path) -> dict:
    if not path.exists():
        logger.warning("配置文件不存在: %s", path)
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        logger.error("配置解析失败: %s - %s", path, e)
        return {}


def get_sources_config() -> dict:
    return load_json_config(SOURCES_CONFIG)


def get_source_config(name: str) -> Optional[dict]:
    cfg = get_sources_config()
    for src in cfg.get("sources", []):
        if src.get("name") == name:
            return src
    return None
