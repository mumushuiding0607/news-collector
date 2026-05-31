"""
Subscription API - 订阅管理
"""
import sys
import hashlib
import random
from datetime import datetime, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "script"))

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from common.db.connection import get_conn

router = APIRouter(prefix="/subscription", tags=["订阅"])


SUBSCRIPTION_PLANS = {
    "pro": {"name": "专业版", "price": 99, "duration_days": 30,
            "description": "解锁全部热点内容，专业级市场分析"},
    "premium": {"name": "高级版", "price": 299, "duration_days": 90,
                "description": "最高权限，机构级决策支持"},
}


class SubscribeRequest(BaseModel):
    level: str


def get_user_from_token(token: str, conn):
    row = conn.execute(
        "SELECT u.id, u.phone, u.nickname, u.subscription_level, u.subscription_expire_at "
        "FROM auth_tokens t JOIN auth_users u ON t.user_id = u.id WHERE t.token = ?",
        (token,)
    ).fetchone()
    return row


@router.get("/plans")
def get_plans():
    plans = []
    for key, info in SUBSCRIPTION_PLANS.items():
        plans.append({
            "level": key,
            "name": info["name"],
            "price": info["price"],
            "duration_days": info["duration_days"],
            "description": info["description"],
        })
    return {"plans": plans}


@router.get("/current")
def get_current_subscription(request: Request):
    conn = get_conn()
    try:
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        user = get_user_from_token(token, conn)
        if not user:
            raise HTTPException(status_code=401, detail="未登录")

        user_id, phone, nickname, level, expire_at = user

        status = "active"
        if expire_at and datetime.strptime(expire_at, "%Y-%m-%d %H:%M:%S") < datetime.now():
            status = "expired"
            level = "free"

        plan = SUBSCRIPTION_PLANS.get(level, {})
        return {
            "level": level,
            "name": plan.get("name", "免费版"),
            "expire_at": expire_at,
            "status": status,
        }
    finally:
        conn.close()


@router.post("/subscribe")
def subscribe(req: SubscribeRequest, request: Request):
    if req.level not in SUBSCRIPTION_PLANS:
        raise HTTPException(status_code=400, detail="无效的订阅级别")

    conn = get_conn()
    try:
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        user = get_user_from_token(token, conn)
        if not user:
            raise HTTPException(status_code=401, detail="请先登录")

        user_id = user[0]
        plan = SUBSCRIPTION_PLANS[req.level]

        start_at = datetime.now()
        end_at = start_at + timedelta(days=plan["duration_days"])

        conn.execute(
            "UPDATE subscription_records SET status = 'cancelled' WHERE user_id = ? AND status = 'active'",
            (user_id,)
        )

        conn.execute(
            "INSERT INTO subscription_records (user_id, level, price, start_at, end_at, status) "
            "VALUES (?, ?, ?, ?, ?, 'active')",
            (user_id, req.level, plan["price"],
             start_at.strftime("%Y-%m-%d %H:%M:%S"),
             end_at.strftime("%Y-%m-%d %H:%M:%S"))
        )

        conn.execute(
            "UPDATE auth_users SET subscription_level = ?, subscription_expire_at = ? WHERE id = ?",
            (req.level, end_at.strftime("%Y-%m-%d %H:%M:%S"), user_id)
        )
        conn.commit()

        return {
            "level": req.level,
            "name": plan["name"],
            "price": plan["price"],
            "start_at": start_at.strftime("%Y-%m-%d %H:%M:%S"),
            "end_at": end_at.strftime("%Y-%m-%d %H:%M:%S"),
            "status": "active",
        }
    finally:
        conn.close()


@router.post("/cancel")
def cancel_subscription(request: Request):
    conn = get_conn()
    try:
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        user = get_user_from_token(token, conn)
        if not user:
            raise HTTPException(status_code=401, detail="请先登录")

        user_id = user[0]

        conn.execute(
            "UPDATE subscription_records SET status = 'cancelled' WHERE user_id = ? AND status = 'active'",
            (user_id,)
        )
        conn.execute(
            "UPDATE auth_users SET subscription_level = 'free', subscription_expire_at = NULL WHERE id = ?",
            (user_id,)
        )
        conn.commit()

        return {"success": True, "message": "已取消订阅"}
    finally:
        conn.close()