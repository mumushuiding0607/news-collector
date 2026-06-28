"""
Subscription API - 订阅管理

只负责路由和参数校验，业务逻辑委托给 core.subscription_service。
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel

from core.subscription_service import (
    get_subscription_plans, get_pay_method, get_personal_qr_image_bytes,
    create_subscription_order, get_order_status,
    activate_subscription_direct, activate_subscription_pending, cancel_subscription,
    get_current_subscription, process_wechat_notify,
    send_payment_notification_email,
    get_user_by_token,
)

router = APIRouter(prefix="/subscription", tags=["订阅"])


class CreateOrderRequest(BaseModel):
    level: str


class ConfirmPaymentRequest(BaseModel):
    order_no: str
    pay_account_note: str  # 用户转账时填写的备注（邮箱/手机号）


# ============ 路由 ============
@router.get("/plans")
def get_plans():
    plans = []
    for key, info in get_subscription_plans().items():
        plans.append({
            "level": key,
            "name": info["name"],
            "price": info["price"],
            "duration_days": info["duration_days"],
            "description": info["description"],
        })
    return {"plans": plans}


@router.get("/pay_method")
def get_pay_method_api():
    """获取当前配置的支付方式"""
    return {"pay_method": get_pay_method()}


@router.get("/personal_qr")
def get_personal_qr_api():
    """获取个人收款码图片"""
    try:
        image_bytes = get_personal_qr_image_bytes()
        return Response(content=image_bytes, media_type="image/jpeg")
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/confirm_payment")
def confirm_payment_api(req: ConfirmPaymentRequest, request: Request):
    """
    用户确认已转账（personal 模式），
    1. 立即激活订阅（pending_confirm 状态）
    2. 发送邮件通知管理员最终确认
    """
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    user = get_user_by_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="请先登录")

    from script.db.auth_db import get_order
    order = get_order(req.order_no)
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    if order[2] != user[0]:  # user_id
        raise HTTPException(status_code=403, detail="无权操作此订单")

    level = order[3]
    plan = get_subscription_plans().get(level, {})
    plan_name = plan.get("name", level)

    # 立即激活订阅（待管理员确认状态）
    activate_subscription_pending(user[0], level)

    # 获取用户邮箱
    user_full = None
    from script.db import auth_db
    try:
        user_full = auth_db.get_user_by_id(user[0])
    except Exception:
        pass
    user_email = user_full[6] if user_full and user_full[6] else "未知"

    ok = send_payment_notification_email(
        order_no=req.order_no,
        user_email=user_email,
        level=level,
        plan_name=plan_name,
        pay_account_note=req.pay_account_note,
    )
    if not ok:
        raise HTTPException(status_code=500, detail="邮件发送失败，请联系管理员")

    return {"success": True, "message": "订阅已生效，请等待管理员最终确认"}


@router.get("/current")
def get_current_subscription_api(request: Request):
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not token:
        raise HTTPException(status_code=401, detail="请先登录")
    result = get_current_subscription(token)
    if not result:
        raise HTTPException(status_code=401, detail="未登录")
    return result


@router.post("/create_order")
def create_order_api(req: CreateOrderRequest, request: Request):
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    user = get_user_by_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="请先登录")

    if req.level not in get_subscription_plans():
        raise HTTPException(status_code=400, detail="无效的订阅级别")

    try:
        return create_subscription_order(user[0], req.level, request)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/order/{order_no}")
def get_order_status_api(order_no: str, request: Request):
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    user = get_user_by_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="请先登录")

    result = get_order_status(order_no)
    if not result:
        raise HTTPException(status_code=404, detail="订单不存在")
    return result


@router.get("/history")
def get_order_history_api(request: Request, limit: int = 20):
    from script.db.auth_db import get_orders_by_user, get_user_by_token as tok
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    user = tok(token)
    if not user:
        raise HTTPException(status_code=401, detail="请先登录")

    orders = get_orders_by_user(user[0], limit)
    return {
        "orders": [
            {
                "order_no": o[1],
                "level": o[2],
                "amount": o[3],
                "status": o[5],
                "trade_no": o[6],
                "created_at": o[7],
            }
            for o in orders
        ]
    }


@router.post("/wechat_notify")
async def wechat_notify_api(request: Request):
    body = await request.body()
    result = process_wechat_notify(body)
    if result["code"] == "SUCCESS":
        return {"code": "SUCCESS", "message": "OK"}
    return {"code": "FAIL", "message": result.get("message", "error")}


@router.post("/subscribe")
def subscribe_api(req: SubscribeRequest, request: Request):
    """直接激活订阅（无需支付，用于测试或内部开通）"""
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    user = get_user_by_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="请先登录")

    try:
        return activate_subscription_direct(user[0], req.level)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/cancel")
def cancel_subscription_api(request: Request):
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    user = get_user_by_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="请先登录")
    cancel_subscription(user[0])
    return {"success": True, "message": "已取消订阅"}