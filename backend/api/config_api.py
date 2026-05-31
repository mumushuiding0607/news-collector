"""
Config API - 应用配置
"""
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
CONFIG_PATH = BASE_DIR / "backend" / "config.json"


def _load_config():
    if not CONFIG_PATH.exists():
        return {}
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def _save_config(data):
    CONFIG_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def get_app_config():
    """获取应用配置"""
    return _load_config()


def update_app_config(data: dict):
    """更新应用配置（仅合并顶级 key）"""
    current = _load_config()
    current.update(data)
    _save_config(current)
    return current