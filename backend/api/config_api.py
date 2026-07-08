"""
Config API - 配置管理

只负责路由和参数校验，业务逻辑委托给 core.config_service。
需要管理员权限。
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from core.config_service import (
    get_app_config, update_app_config,
    get_env_config, update_env_config,
    get_full_config, get_public_config,
    get_app_version_config, update_app_version_config,
    get_sources_config, update_sources_config,
)
import json
from pathlib import Path
from backend.api._auth import require_admin

router = APIRouter(prefix="/config", tags=["配置"])


class UpdateConfigRequest(BaseModel):
    key: str
    value: str


class BatchUpdateConfigRequest(BaseModel):
    app_config: dict | None = None
    env_config: dict | None = None


@router.get("/public")
def get_config_public(request: Request):
    """
    获取公开配置（无需认证）
    供前端在未登录状态下获取锁定规则、UI文本等功能配置。
    """
    return get_public_config()


@router.get("/version")
def get_version_config(request: Request):
    """
    获取应用版本信息（无需认证）
    供前端检查更新使用
    """
    return get_app_version_config()


@router.post("/version")
def post_version_config(request: Request, updates: dict):
    """
    更新应用版本配置（需要管理员权限）
    """
    require_admin(request)
    try:
        return update_app_version_config(updates)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("")
def get_config(request: Request):
    """获取完整配置"""
    require_admin(request)
    return get_full_config()


@router.get("/app")
def get_config_app(request: Request):
    """获取应用配置（config.json）"""
    require_admin(request)
    return get_app_config()


@router.post("/app")
def update_config_app(request: Request, updates: dict):
    """
    更新应用配置（部分更新）
    传入 {"app_name": "新名称", "subscription_pay_method": "wechat"}
    """
    require_admin(request)
    try:
        return update_app_config(updates)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/env")
def get_config_env(request: Request):
    """获取环境变量配置（.env）"""
    require_admin(request)
    return get_env_config()


@router.post("/env")
def update_config_env(request: Request, updates: dict):
    """
    更新环境变量配置
    传入 {"ADMIN_EMAIL": "admin@example.com", "SMTP_HOST": "smtp.example.com"}
    """
    require_admin(request)
    try:
        return update_env_config(updates)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/batch")
def batch_update_config(request: Request, body: BatchUpdateConfigRequest):
    """
    批量更新配置（同时更新 app_config 和 env_config）
    """
    require_admin(request)
    result = {}
    if body.app_config:
        result["app_config"] = update_app_config(body.app_config)
    if body.env_config:
        result["env_config"] = update_env_config(body.env_config)
    return result


@router.get("/subscription_tiers")
def get_subscription_tiers(request: Request):
    """获取订阅套餐列表"""
    require_admin(request)
    cfg = get_app_config()
    return {"subscription_tiers": cfg.get("subscription_tiers", [])}


@router.post("/subscription_tiers")
def update_subscription_tiers(request: Request, tiers: list[dict]):
    """
    全量替换订阅套餐列表
    每个套餐: {level, name, price, duration_days, description, features}
    """
    require_admin(request)
    cfg = get_app_config()
    cfg["subscription_tiers"] = tiers
    update_app_config({"subscription_tiers": tiers})
    return {"subscription_tiers": tiers}


@router.get("/sources")
def get_config_sources(request: Request):
    """获取 sources.json 爬虫配置"""
    require_admin(request)
    return get_sources_config()


@router.post("/sources")
def update_config_sources(request: Request, updates: dict):
    """
    更新 sources.json 爬虫配置（部分更新）
    传入 {"crawNumPerSource": 50} 或 {"newsCache": {"minScore": 10}}
    """
    require_admin(request)
    try:
        return update_sources_config(updates)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== 侧边栏菜单配置 ====================
_SIDEBAR_MENU_PATH = Path(__file__).resolve().parent.parent / "config" / "sidebar_menu.json"
_cached_sidebar_menu: dict | None = None


def get_sidebar_menu_config() -> dict:
    """读取侧边栏菜单配置（首次调用时缓存）"""
    global _cached_sidebar_menu
    if _cached_sidebar_menu is None:
        if _SIDEBAR_MENU_PATH.exists():
            _cached_sidebar_menu = json.loads(_SIDEBAR_MENU_PATH.read_text(encoding="utf-8"))
        else:
            _cached_sidebar_menu = {"default": "stock", "newsTypes": {}}
    return _cached_sidebar_menu


@router.get("/sidebar_menu")
def get_sidebar_menu(request: Request):
    """
    获取侧边栏菜单配置（无需管理员权限）
    返回各新闻类型对应的菜单项
    """
    return get_sidebar_menu_config()