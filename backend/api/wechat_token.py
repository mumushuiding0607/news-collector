# -*- coding: UTF-8 -*-
"""
WeChat Token API - 微信公众号 access_token 获取接口

接收 appid 和 appsecret，返回 access_token（缓存优先，过期自动刷新）
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from .wx_token_manager import get_wx_token_manager

router = APIRouter(prefix="/wechat", tags=["微信"])


@router.get("/token")
def get_wechat_token(appid: str, appsecret: str):
    """
    获取微信公众号 access_token

    - **appid**: 微信公众号 AppID
    - **appsecret**: 微信公众号 AppSecret

    优先返回缓存，缓存过期后自动刷新。
    """
    if not appid or not appsecret:
        raise HTTPException(status_code=400, detail="appid 和 appsecret 不能为空")

    manager = get_wx_token_manager()
    token = manager.get_access_token(appid, appsecret)

    if not token:
        raise HTTPException(
            status_code=500,
            detail="获取 access_token 失败，请检查 appid 和 appsecret 是否正确，或服务器 IP 是否在微信白名单中",
        )

    return {"access_token": token}
