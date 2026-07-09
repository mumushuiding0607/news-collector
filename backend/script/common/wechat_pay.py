"""
WeChat Pay API 工具

支持：
- Native QR 支付（PC 网页）
- H5 支付（Mobile 微信内）

文档：https://pay.weixin.qq.com/wiki/doc/apiv3/apis/index.shtml
"""

import hashlib
import os
import random
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Optional

import requests


@dataclass
class WeChatPayResult:
    code_url: str  # Native 用，用于生成 QR 码
    prepay_id: str  # H5 用，拼接 mweb_url


class WeChatPayAPI:
    """微信支付 API v3"""

    def __init__(
        self,
        mchid: str,
        serial_no: str,
        private_key: str,
        apiv3_key: str,
        appid: str,
    ):
        self.mchid = mchid
        self.serial_no = serial_no
        self.private_key = private_key
        self.apiv3_key = apiv3_key
        self.appid = appid
        self._token_cache: Optional[tuple] = None

    # ------------------------------------------------------------------
    # 鉴权
    # ------------------------------------------------------------------

    def _get_access_token(self) -> str:
        """获取调用凭证（简化版，实际生产应用用 authorizer_access_token）"""
        raise NotImplementedError("请使用代制提供的方式获取 token")

    def _make_signature(self, method: str, url_path: str, timestamp: str, nonce: str, body: str) -> str:
        """构建 API v3 签名"""
        import base64
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding
        from cryptography.hazmat.backends import default_backend

        message = f"{method}\n{url_path}\n{timestamp}\n{nonce}\n{body}\n"
        message_bytes = message.encode("utf-8")

        # 使用私钥签名
        key = serialization.load_pem_private_key(
            self.private_key.encode("utf-8"),
            password=None,
            backend=default_backend(),
        )
        sig = key.sign(message_bytes, padding.PKCS1v15(), hashes.SHA256())
        return base64.b64encode(sig).decode("utf-8")

    def _sign_str(self, timestamp: str, nonce: str, body: str) -> str:
        """拼装签名串"""
        return f"{timestamp}\n{nonce}\n{body}\n"

    def _build_auth_header(self, method: str, url_path: str, body: str = "") -> dict:
        """构建鉴权 Header"""
        timestamp = str(int(time.time()))
        nonce = str(random.randint(100000, 999999))
        signature = self._make_signature(method, url_path, timestamp, nonce, body)
        return {
            "Authorization": f'WECHATPAY2-SHA256-RSA2048 mchid="{self.mchid}",'
                              f'serial_no="{self.serial_no}",'
                              f'nonce_str="{nonce}",'
                              f'signature="{signature}",'
                              f'timestamp="{timestamp}",'
                              f'signature_headers="wechatpay-timestamp,wechatpay-nonce,wechatpay-signature"',
            "Content-Type": "application/json",
            "Wechatpay-Serial": self.serial_no,
        }

    # ------------------------------------------------------------------
    # JSAPI / Native / H5 下单
    # ------------------------------------------------------------------

    def _unified_order(
        self,
        description: str,
        out_trade_no: str,
        amount: int,
        notify_url: str,
        attach: str = "",
    ) -> dict:
        """
        统一下单（Native + H5）
        amount: 金额（分）
        """
        url = "https://api.mch.weixin.qq.com/v3/pay/transactions/native"
        url_path = "/v3/pay/transactions/native"
        payload = {
            "mchid": self.mchid,
            "out_trade_no": out_trade_no,
            "appid": self.appid,
            "description": description,
            "notify_url": notify_url,
            "amount": {"total": amount, "currency": "CNY"},
            "attach": attach,
        }

        import json
        body = json.dumps(payload)
        headers = self._build_auth_header("POST", url_path, body)

        resp = requests.post(url, data=body, headers=headers, timeout=10)
        if resp.status_code != 200:
            raise Exception(f"WeChat Pay API error: {resp.status_code} {resp.text}")
        return resp.json()

    def native_qr_order(
        self,
        description: str,
        out_trade_no: str,
        amount: int,
        notify_url: str,
        attach: str = "",
    ) -> str:
        """Native QR 码支付，返回 code_url（用于生成 QR）"""
        result = self._unified_order(description, out_trade_no, amount, notify_url, attach)
        return result["code_url"]

    def h5_order(
        self,
        description: str,
        out_trade_no: str,
        amount: int,
        notify_url: str,
        h5_redirect_url: str,
        attach: str = "",
    ) -> str:
        """
        H5 支付，返回 mweb_url（拉起微信支付）
        h5_redirect_url: 支付完成跳转页面
        """
        url = "https://api.mch.weixin.qq.com/v3/pay/transactions/h5"
        url_path = "/v3/pay/transactions/h5"

        import json
        payload = {
            "mchid": self.mchid,
            "out_trade_no": out_trade_no,
            "appid": self.appid,
            "description": description,
            "notify_url": notify_url,
            "amount": {"total": amount, "currency": "CNY"},
            "scene_info": {
                "payer_client_ip": os.environ.get("SERVER_IP", ""),
                "h5_info": {"type": "Wap"},
            },
            "h5": {"type": "Wap", "wap_url": h5_redirect_url, "wap_name": "新闻看板"},
            "attach": attach,
        }
        body = json.dumps(payload)
        headers = self._build_auth_header("POST", url_path, body)

        resp = requests.post(url, data=body, headers=headers, timeout=10)
        if resp.status_code != 200:
            raise Exception(f"WeChat Pay H5 API error: {resp.status_code} {resp.text}")
        return resp.json().get("h5_url", "")

    def query_order(self, out_trade_no: str) -> dict:
        """查询订单状态"""
        url = f"https://api.mch.weixin.qq.com/v3/pay/transactions/out-trade-no/{out_trade_no}?mchid={self.mchid}"
        url_path = f"/v3/pay/transactions/out-trade-no/{out_trade_no}"

        headers = self._build_auth_header("GET", url_path)
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code != 200:
            raise Exception(f"WeChat Pay query error: {resp.status_code} {resp.text}")
        return resp.json()


# ---------------------------------------------------------------------------
# 配置（从环境变量读取，敏感信息勿提交 Git）
# ------------------------------------------------------------------------

_WECHAT_CONFIG: Optional[dict] = None


def _load_wechat_config() -> dict:
    global _WECHAT_CONFIG
    if _WECHAT_CONFIG is not None:
        return _WECHAT_CONFIG

    import os
    from pathlib import Path

    env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

    _WECHAT_CONFIG = {
        "mchid": os.environ.get("WECHAT_MCHID", ""),
        "serial_no": os.environ.get("WECHAT_SERIAL_NO", ""),
        "private_key": os.environ.get("WECHAT_PRIVATE_KEY", ""),
        "apiv3_key": os.environ.get("WECHAT_APIV3_KEY", ""),
        "appid": os.environ.get("WECHAT_APPID", ""),
        "notify_url": os.environ.get("WECHAT_NOTIFY_URL", ""),
    }
    return _WECHAT_CONFIG


def get_wechat_api() -> Optional[WeChatPayAPI]:
    """获取微信支付 API 实例（未配置时返回 None）"""
    cfg = _load_wechat_config()
    if not cfg.get("mchid") or not cfg.get("private_key"):
        return None
    return WeChatPayAPI(
        mchid=cfg["mchid"],
        serial_no=cfg["serial_no"],
        private_key=cfg["private_key"],
        apiv3_key=cfg["apiv3_key"],
        appid=cfg["appid"],
    )