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
)
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