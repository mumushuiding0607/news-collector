"""
subscription_service.py - 订阅业务服务

从 api/subscription.py 提取的业务逻辑，包括：
- 订阅计划定义
- 订单创建（mock / personal / wechat 三种支付方式）
- 微信支付回调解析
- 订阅激活 / 取消
"""
from __future__ import annotations

import os
import random
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from script.db import auth_db
from core.config_service import get_app_name
from script.db.subscription_db import (
    activate_subscription as _activate_subscription,
    activate_subscription_pending as _activate_subscription_pending,
    cancel_active_subscription as _cancel_active_subscription,
    cancel_subscription_full,
)


# 项目根目录（backend/ 的上一级）
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_CONFIG_PATH = _PROJECT_ROOT / "backend" / "config.json"
_PERSONAL_QR_PATH = _PROJECT_ROOT / "pay" / "wechat.jpg"


def _load_config() -> dict:
    """读取 config.json"""
    if not _CONFIG_PATH.exists():
        return {}
    import json
    return json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))


def _get_subscription_tiers_from_config() -> dict:
    """从 config.json 的 subscription_tiers 加载套餐字典，key 为 level"""
    cfg = _load_config()
    tiers = cfg.get("subscription_tiers", [])
    return {t["level"]: t for t in tiers}


# ============ 配置 ============
def get_subscription_plans() -> dict:
    """获取订阅套餐字典（从 config.json 读取）"""
    return _get_subscription_tiers_from_config()


def get_pay_method() -> str:
    """获取支付方式：mock | personal | wechat"""
    cfg = _load_config()
    return cfg.get("subscription_pay_method", "wechat")


def get_personal_qr_image_path() -> Path:
    """获取个人收款码图片路径"""
    return _PERSONAL_QR_PATH


def get_personal_qr_image_bytes() -> bytes:
    """获取个人收款码图片二进制"""
    path = get_personal_qr_image_path()
    if path.exists():
        return path.read_bytes()
    raise FileNotFoundError(f"收款码图片不存在: {path}")


def _get_admin_email() -> str:
    """获取管理员邮箱"""
    env_path = _PROJECT_ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                if k.strip() == "ADMIN_EMAIL":
                    return v.strip()
    return os.environ.get("ADMIN_EMAIL", "")


def _send_admin_email(subject: str, body: str) -> bool:
    """发送邮件给管理员（调用统一邮件服务）"""
    admin_email = _get_admin_email()
    if not admin_email:
        print(f"[邮件] ADMIN_EMAIL 未配置，跳过发送: {subject}")
        return False

    from core.email_service import send_email
    return send_email(admin_email, subject, body)


def send_payment_notification_email(order_no: str, user_email: str,
                                    level: str, plan_name: str,
                                    pay_account_note: str) -> bool:
    """发送付款通知邮件给管理员"""
    subject = f"【待激活】用户已转账订阅 {plan_name}"
    body = f"""
您收到一笔订阅付款待确认：

订单号：{order_no}
订阅级别：{plan_name}
用户账户：{user_email}
转账备注：{pay_account_note}

请登录管理后台确认用户付款后，手动激活该用户的订阅。
"""
    return _send_admin_email(subject, body)


def send_rejection_email(user_id: int, level: str, reason: str = "") -> bool:
    """发送付款被拒绝邮件给用户，要求上传付款凭证"""
    from script.db.auth_db import get_user_by_id
    user = get_user_by_id(user_id)
    if not user:
        return False
    email = user[6] if len(user) > 6 else None
    phone = user[1]
    if not email:
        print(f"[邮件] 用户 {user_id} 无邮箱，跳过拒绝邮件")
        return False

    plan = get_subscription_plans().get(level, {})
    plan_name = plan.get("name", level)
    plan_price = plan.get("price", "?")

    subject = f"【{get_app_name()}】订阅付款待核实，请回复邮件上传付款凭证"
    body = f"""
您好，您的订阅付款需要核实：

订阅套餐：{plan_name}
付款金额：¥{plan_price}
原因：{reason or "管理员未收到您的付款凭证，请回复本邮件上传付款截图，以便核实后开通服务。"}

请直接回复此邮件，附上您的付款截图，我们将尽快为您开通服务。

如有疑问，请联系客服。
"""
    from core.email_service import send_email
    return send_email(email, subject, body)


def generate_order_no() -> str:
    """生成订单号：NC{timestamp}{6位随机}"""
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    rnd = str(random.randint(100000, 999999))
    return f"NC{ts}{rnd}"


# ============ 用户信息 ============
def get_user_by_token(token: str) -> Optional[tuple]:
    return auth_db.get_user_by_token(token)


# ============ 订单创建 ============
def create_subscription_order(user_id: int, level: str,
                              request=None) -> dict:
    """
    创建订阅订单，根据配置的支付方式返回对应状态。

    返回 dict 包含：order_no, level, price, status
    """
    if level not in get_subscription_plans():
        raise ValueError("无效的订阅级别")

    plan = get_subscription_plans()[level]
    order_no = generate_order_no()
    amount = int(plan["price"] * 100)  # 分为单位
    expire_at = (datetime.now() + timedelta(minutes=30)).strftime("%Y-%m-%d %H:%M:%S")
    description = f"{get_app_name()}-{plan['name']}订阅"
    pay_method = get_pay_method()

    wechat_code_url = None
    wechat_prepay_id = None
    order_status = "pending"

    if pay_method == "mock":
        order_status = "mock"
    elif pay_method == "personal":
        order_status = "personal_pending"
    elif pay_method == "wechat":
        # 必须使用真实微信支付，配置缺失直接报错
        from script.common.wechat_pay import get_wechat_api
        wechat = get_wechat_api()
        if not wechat:
            raise RuntimeError("微信支付未配置，请联系管理员")
        if request is None:
            raise RuntimeError("缺少请求上下文，无法创建订单")

        ua = request.headers.get("User-Agent", "").lower()
        if "micromessenger" in ua or "mobile" in ua:
            notify_url = "https://news.mmmini.com/api/subscription/wechat_notify"
            redirect_url = "https://news.mmmini.com/subscription"
            h5_url = wechat.h5_order(
                description=description,
                out_trade_no=order_no,
                amount=amount,
                notify_url=notify_url,
                h5_redirect_url=redirect_url,
            )
            order_status = "h5_created"
        else:
            notify_url = "https://news.mmmini.com/api/subscription/wechat_notify"
            code_url = wechat.native_qr_order(
                description=description,
                out_trade_no=order_no,
                amount=amount,
                notify_url=notify_url,
            )
            wechat_code_url = code_url
            order_status = "qr_created"

    # 保存订单（pay_method 字段记录配置值）
    from script.db.auth_db import create_order as _create_order
    _create_order(
        order_no=order_no,
        user_id=user_id,
        level=level,
        amount=plan["price"],
        pay_method=pay_method,
        expire_at=expire_at,
        wechat_code_url=wechat_code_url,
        wechat_prepay_id=wechat_prepay_id,
    )

    result = {
        "order_no": order_no,
        "level": level,
        "price": plan["price"],
        "status": order_status,
        "pay_method": pay_method,
    }
    if order_status == "qr_created":
        result["code_url"] = wechat_code_url
    elif order_status == "h5_created":
        result["h5_url"] = h5_url

    return result


# ============ 订单状态 ============
def get_order_status(order_no: str) -> dict | None:
    """获取订单信息"""
    from script.db.auth_db import get_order as _get_order
    order = _get_order(order_no)
    if not order:
        return None
    # expire_at 是第 12 个字段
    expire_at = order[12]
    if expire_at and datetime.strptime(expire_at, "%Y-%m-%d %H:%M:%S") < datetime.now():
        if order[6] == "pending":  # status 是第 7 个字段
            from script.db.subscription_db import mark_order_expired
            mark_order_expired(order_no)
            order = _get_order(order_no)
    return {
        "order_no": order[1],
        "level": order[3],
        "amount": order[4],
        "status": order[6],
        "trade_no": order[7],
        "created_at": order[10],
    }


# ============ 微信回调 ============
def parse_wechat_notify(body_bytes: bytes) -> dict:
    """解析微信支付回调 XML"""
    root = ET.fromstring(body_bytes.decode("utf-8"))
    def find_text(elem, tag):
        e = elem.find(tag)
        return e.text if e is not None else ""
    return {
        "return_code": find_text(root, "return_code"),
        "out_trade_no": find_text(root, "out_trade_no"),
        "transaction_id": find_text(root, "transaction_id"),
        "total": find_text(root, "total"),
    }


def process_wechat_notify(body_bytes: bytes) -> dict:
    """处理微信支付回调"""
    result = parse_wechat_notify(body_bytes)
    if result["return_code"] != "SUCCESS":
        return {"code": "FAIL", "message": "return_code not SUCCESS"}

    out_trade_no = result["out_trade_no"]
    if not out_trade_no:
        return {"code": "FAIL", "message": "missing out_trade_no"}

    from script.db.auth_db import update_order_paid
    update_order_paid(out_trade_no, result["transaction_id"])

    from script.db.auth_db import get_order
    order = get_order(out_trade_no)
    if not order:
        return {"code": "FAIL", "message": "order not found"}

    user_id = order[2]
    level = order[3]
    plan = get_subscription_plans().get(level)
    if not plan:
        return {"code": "FAIL", "message": "plan not found"}

    start_at = datetime.now()
    end_at = start_at + timedelta(days=plan["duration_days"])
    _activate_subscription(user_id, level, plan["price"], start_at, end_at)
    return {"code": "SUCCESS", "message": "OK"}


# ============ 订阅激活 / 取消 ============
def activate_subscription_direct(user_id: int, level: str) -> dict:
    """直接激活订阅（无需支付，用于测试或内部开通）"""
    if level not in get_subscription_plans():
        raise ValueError("无效的订阅级别")
    plan = get_subscription_plans()[level]
    start_at = datetime.now()
    end_at = start_at + timedelta(days=plan["duration_days"])
    _activate_subscription(user_id, level, plan["price"], start_at, end_at)
    return {
        "level": level,
        "name": plan["name"],
        "price": plan["price"],
        "start_at": start_at.strftime("%Y-%m-%d %H:%M:%S"),
        "end_at": end_at.strftime("%Y-%m-%d %H:%M:%S"),
        "status": "active",
    }


def activate_subscription_pending(user_id: int, level: str) -> dict:
    """用户确认付款后直接激活（待管理员最终确认），订阅立即生效"""
    if level not in get_subscription_plans():
        raise ValueError("无效的订阅级别")
    plan = get_subscription_plans()[level]
    start_at = datetime.now()
    end_at = start_at + timedelta(days=plan["duration_days"])
    _activate_subscription_pending(user_id, level, plan["price"], start_at, end_at)
    return {
        "level": level,
        "name": plan["name"],
        "price": plan["price"],
        "start_at": start_at.strftime("%Y-%m-%d %H:%M:%S"),
        "end_at": end_at.strftime("%Y-%m-%d %H:%M:%S"),
        "status": "pending_confirm",
    }


def cancel_subscription(user_id: int) -> None:
    """取消当前订阅"""
    cancel_subscription_full(user_id)


# ============ 当前订阅信息 ============
def get_current_subscription(token: str) -> dict | None:
    """获取当前用户订阅状态"""
    user = get_user_by_token(token)
    if not user:
        return None
    user_id, phone, nickname, level, expire_at = user[0], user[1], user[2], user[3], user[4]
    status = "active"
    if expire_at and datetime.strptime(expire_at, "%Y-%m-%d %H:%M:%S") < datetime.now():
        status = "expired"
        level = "free"
    plan = get_subscription_plans().get(level, {})
    return {
        "level": level,
        "name": plan.get("name", "免费版"),
        "expire_at": expire_at,
        "status": status,
    }