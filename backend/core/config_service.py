"""
config_service.py - 配置管理业务服务

处理 news_collector 项目所有配置文件的读取和修改：
- backend/config.json（应用主配置）
- .env（环境变量）
- 其他配置文件
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from script.common.jsonutil import write_json

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_CONFIG_PATH = _PROJECT_ROOT / "backend" / "config.json"
# .env 实际位于 backend/ 下（与 config.json 同目录），而非项目根。
# 之前指错位置导致 get_env_config() 永远返回 {}，UPDATE_APK_URL_PREFIX 拿不到 →
# /api/config/version 接口不返回 update_url → 前端"立即更新"点击无反应。
_ENV_PATH = _PROJECT_ROOT / "backend" / ".env"


def _load_json_config(path: Path) -> dict:
    """读取 JSON 配置文件"""
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _save_json_config(path: Path, data: dict) -> None:
    """保存 JSON 配置文件"""
    write_json(data, path)


def get_app_config() -> dict:
    """获取应用主配置（config.json）"""
    return _load_json_config(_CONFIG_PATH)


def get_public_config() -> dict:
    """
    获取公开配置（无需认证，供前端使用）
    返回 config.json 全部内容。
    """
    return get_app_config()


def _deep_merge(base: dict, updates: dict) -> dict:
    """深度合并字典，updates 覆盖 base 中的同名 key（递归合并嵌套 dict）"""
    result = base.copy()
    for key, value in updates.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def update_app_config(updates: dict) -> dict:
    """
    更新应用配置（部分更新，深度合并嵌套 dict）
    例如：update_app_config({"app_name": "新名称"})
    例如：update_app_config({"features": {"subscription_enabled": false}})
    """
    current = _load_json_config(_CONFIG_PATH)
    current = _deep_merge(current, updates)
    _save_json_config(_CONFIG_PATH, current)
    return current


def get_app_name() -> str:
    """获取应用名称"""
    return get_app_config().get("app_name", "新闻看板")


def get_env_config() -> dict:
    """获取 .env 环境变量配置"""
    env_vars = {}
    if _ENV_PATH.exists():
        for line in _ENV_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                env_vars[k.strip()] = v.strip()
    return env_vars


def update_env_config(updates: dict) -> dict:
    """
    更新 .env 环境变量配置
    例如：update_env_config({"ADMIN_EMAIL": "admin@example.com"})
    """
    env_vars = get_env_config()
    env_vars.update(updates)

    lines = []
    for k, v in env_vars.items():
        lines.append(f"{k}={v}")

    _ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return env_vars


def get_full_config() -> dict:
    """获取完整配置（包含 JSON 配置和环境变量）"""
    return {
        "app_config": get_app_config(),
        "env_config": get_env_config(),
    }


def get_app_version_config() -> dict:
    """
    获取应用版本配置（包含动态构建的 update_url）
    update_url 根据 .env 中的 UPDATE_APK_URL_PREFIX 和渠道配置动态生成
    """
    config = _load_json_config(_CONFIG_PATH)
    version_config = config.get("app_version", {})

    # 从 .env 读取更新配置
    env_vars = get_env_config()
    apk_prefix = env_vars.get("UPDATE_APK_URL_PREFIX", "")
    channel = env_vars.get("UPDATE_CHANNEL", "self_hosted")
    channels = version_config.get("update_channels", {})

    # 动态构建 update_url
    latest_version = version_config.get("latest_version", "1.0.0")
    latest_build = version_config.get("latest_build", 1)

    if channel == "self_hosted" and apk_prefix:
        self_hosted = channels.get("self_hosted", {})
        if self_hosted.get("enabled"):
            pattern = self_hosted.get("filename_pattern", "news_board_{version}.apk")
            filename = pattern.replace("{version}", latest_version)
            version_config["update_url"] = f"{apk_prefix}/{filename}"
            version_config["channel"] = "self_hosted"
    elif channel in ("huawei", "xiaomi", "both"):
        version_config["channel"] = channel

    # 移除敏感信息
    version_config.pop("update_channels", None)

    return version_config


def update_app_version_config(updates: dict) -> dict:
    """更新应用版本配置（部分更新）"""
    current = _load_json_config(_CONFIG_PATH)
    if "app_version" not in current:
        current["app_version"] = {}
    current["app_version"].update(updates)
    _save_json_config(_CONFIG_PATH, current)
    return current["app_version"]


def get_sources_config() -> dict:
    """获取 sources.json 爬虫配置"""
    sources_path = _PROJECT_ROOT / "backend" / "config" / "sources.json"
    return _load_json_config(sources_path)


def update_sources_config(updates: dict) -> dict:
    """
    更新 sources.json 爬虫配置（部分更新，深度合并嵌套 dict）
    例如：update_sources_config({"crawNumPerSource": 50})
    例如：update_sources_config({"newsCache": {"minScore": 10}})
    """
    sources_path = _PROJECT_ROOT / "backend" / "config" / "sources.json"
    current = _load_json_config(sources_path)
    current = _deep_merge(current, updates)
    _save_json_config(sources_path, current)
    return current