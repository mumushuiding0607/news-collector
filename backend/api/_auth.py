"""
backend/api/_auth.py - Shared authentication helpers for API routes
"""

from fastapi import Request, HTTPException


def get_user_email(request: Request) -> str | None:
    """从请求中获取当前用户邮箱（通过 Bearer token）"""
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not token:
        return None
    from script.db.auth_db import get_user_by_token
    user = get_user_by_token(token)
    if not user:
        return None
    # user = (id, phone, email, nickname, subscription_level, subscription_expire_at)
    return user[2] if len(user) > 2 else None


def require_admin(request: Request):
    """验证是否为管理员，非管理员抛出 403"""
    from backend.core.admin_service import is_admin_email
    email = get_user_email(request)
    if not email or not is_admin_email(email):
        raise HTTPException(status_code=403, detail="需要管理员权限")
