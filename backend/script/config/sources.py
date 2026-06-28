"""
config/sources.py - 数据源配置管理

从 sources.json 加载数据源配置。
"""

import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_SOURCES_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "sources.json"


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
    return load_json_config(_SOURCES_PATH)


def get_source_config(name: str) -> Optional[dict]:
    cfg = get_sources_config()
    for src in cfg.get("sources", []):
        if src.get("name") == name:
            return src
    return None