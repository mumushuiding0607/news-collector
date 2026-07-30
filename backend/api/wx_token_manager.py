# -*- coding: UTF-8 -*-
"""
微信公众号 access_token 管理器（独立模块）

设计原则:
- 与 wx_publisher.py 解耦,只负责 token 的获取/缓存/刷新
- 单例 key-value 缓存,按 appid 维度隔离 (支持多账号)
- 提前 1 分钟过期,避免临界值出错
- errcode 友好映射 (40164 IP白名单 / 40001 AppSecret 错 / 40013 AppID 错 / 45009 调用超限)
"""
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, Optional

import requests

WX_BASE_URL = "https://api.weixin.qq.com/cgi-bin"


class WxTokenManager:
    """单例: 所有 WeixinPublisher 实例共享 token 缓存"""

    _instance: Optional["WxTokenManager"] = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return
        self._initialized = True
        # key: appid, value: {"access_token": str, "expires_at": datetime}
        self._cache: Dict[str, Dict] = {}
        self._lock = threading.Lock()  # 进程内锁,单实例多线程安全

    def get_access_token(self, app_id: str, app_secret: str) -> Optional[str]:
        """
        获取并缓存 access_token
        - 若 appid 对应 token 未过期, 直接返回
        - 否则调用微信 /token 接口刷新
        - 失败返回 None, 调用方决定如何处理
        """
        cached = self._get_cached(app_id)
        if cached:
            return cached

        return self._refresh(app_id, app_secret)

    def _get_cached(self, app_id: str) -> Optional[str]:
        with self._lock:
            data = self._cache.get(app_id)
            if not data:
                return None
            if data["expires_at"] > datetime.now() + timedelta(minutes=1):
                return data["access_token"]
            return None

    def _refresh(self, app_id: str, app_secret: str) -> Optional[str]:
        url = (
            f"{WX_BASE_URL}/token"
            f"?grant_type=client_credential&appid={app_id}&secret={app_secret}"
        )

        try:
            resp = requests.get(url, timeout=5)
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            print(f"[WxToken] HTTP 请求失败: {e}")
            return None

        access_token = data.get("access_token")
        expires_in = data.get("expires_in")

        if not access_token:
            errcode = data.get("errcode")
            print(f"[WxToken] 获取 access_token 失败: {data}")
            self._diagnose_error(errcode)
            return None

        with self._lock:
            self._cache[app_id] = {
                "access_token": access_token,
                "expires_at": datetime.now() + timedelta(seconds=expires_in),
            }

        print(f"[WxToken] 已刷新 appid={app_id[:8]}... 的 access_token (有效期 {expires_in}s)")
        return access_token

    def _diagnose_error(self, errcode):
        """对常见 errcode 给出人类可读的修复建议"""
        messages = {
            40164: "★ 解决方案: 服务器 IP 不在白名单。请到 mp.weixin.qq.com → 设置与开发 → 基本配置 → IP 白名单 → 添加本服务器公网 IP",
            40001: "★ 解决方案: AppSecret 错误,或在微信后台重置后再试",
            40013: "★ 解决方案: AppID 无效,请核对公众号基本配置",
            45009: "★ 解决方案: 调用次数超限,默认每天 2000 次,需申请提高配额",
            40125: "★ 解决方案: 启用 AppSecret 错误,需在微信后台启用",
            40004: "★ 解决方案: AppSecret 失效,请重置后再试",
        }
        msg = messages.get(errcode, f"★ 未识别的 errcode {errcode}, 请查 https://developers.weixin.qq.com/doc/service/api/msg/errcode")
        print(msg)

    # ---- 测试/调试用 ----
    def clear_cache(self, app_id: Optional[str] = None):
        """清空缓存 (测试时强制刷新用)"""
        with self._lock:
            if app_id:
                self._cache.pop(app_id, None)
            else:
                self._cache.clear()


def get_wx_token_manager() -> WxTokenManager:
    """全局快捷方法"""
    return WxTokenManager()
