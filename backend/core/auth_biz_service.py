"""
auth_biz_service.py - 认证业务逻辑层

依赖基础设施层（auth_code_service）提供的能力，
实现用户注册、登录、资料更新等业务逻辑。
"""
from __future__ import annotations

from typing import Optional

from script.db import auth_db
from script.db.auth_db import get_user_by_token as _get_user_by_token_db

from core.auth_code_service import (
    hash_password,
    generate_token,
    validate_phone,
    validate_email,
)


# ============ 用户信息获取 ============
def get_user_by_token(token: str) -> Optional[tuple]:
    return _get_user_by_token_db(token)


# ============ 注册 / 登录 ============
def register_by_phone(phone: str, password: str) -> tuple:
    """手机号注册，返回 (token, user_id)"""
    if not validate_phone(phone):
        raise ValueError("手机号格式不正确")
    if len(password) < 6:
        raise ValueError("密码至少6位")
    if auth_db.phone_exists(phone):
        raise ValueError("手机号已注册")

    password_hash = hash_password(password)
    user_id = auth_db.create_user(phone, password_hash, email=None)
    token = generate_token()
    auth_db.create_token(user_id, token)
    return token, user_id


def login_by_phone_code(phone: str, code: str) -> tuple:
    """验证码登录（不存在则自动注册），返回 (token, user_id)"""
    if not validate_phone(phone):
        raise ValueError("手机号格式不正确")
    if auth_db.is_login_locked(phone):
        raise ValueError("登录次数过多，请5分钟后再试")

    stored_code = auth_db.get_valid_phone_code(phone)
    if not stored_code or stored_code != code:
        auth_db.record_login_attempt(phone, success=False)
        raise ValueError("验证码错误或已过期")

    user_row = auth_db.get_user_by_phone(phone)
    if not user_row:
        user_id = auth_db.create_user(phone, password_hash="", email=None)
    else:
        user_id = user_row[0]

    auth_db.mark_phone_code_used(phone)
    token = generate_token()
    auth_db.create_token(user_id, token)
    auth_db.record_login_attempt(phone, success=True)
    return token, user_id


def login_by_password(email: str, password: str) -> tuple:
    """密码登录，返回 (token, user_row)"""
    if not validate_email(email):
        raise ValueError("邮箱格式不正确")

    user_row = auth_db.get_user_by_email(email)
    if not user_row:
        raise ValueError("用户不存在")
    if not user_row[2]:
        raise ValueError("请先使用验证码登录")
    if hash_password(password) != user_row[2]:
        raise ValueError("密码错误")

    token = generate_token()
    auth_db.create_token(user_row[0], token)
    return token, user_row


def email_register(email: str, code: str, password: str) -> tuple:
    """邮箱验证码注册，返回 (token, user_id)"""
    if not validate_email(email):
        raise ValueError("邮箱格式不正确")
    if len(password) < 6:
        raise ValueError("密码至少6位")
    if auth_db.check_email_exists(email):
        raise ValueError("邮箱已被注册")

    stored_code = auth_db.get_valid_email_code(email)
    if not stored_code or stored_code != code:
        raise ValueError("验证码错误或已过期")

    password_hash = hash_password(password)
    user_id = auth_db.create_user(phone=None, password_hash=password_hash, email=email)
    token = generate_token()
    auth_db.create_token(user_id, token)
    auth_db.mark_email_code_used(email)
    return token, user_id


def reset_password(email: str, code: str, new_password: str) -> bool:
    """重置密码"""
    if not validate_email(email):
        raise ValueError("邮箱格式不正确")
    if len(new_password) < 6:
        raise ValueError("新密码至少6位")

    stored_code = auth_db.get_valid_reset_code(email)
    if not stored_code or stored_code != code:
        raise ValueError("验证码错误或已过期")

    user_row = auth_db.get_user_by_email(email)
    if not user_row:
        raise ValueError("用户不存在")

    auth_db.update_user_password_by_email(email, hash_password(new_password))
    auth_db.mark_reset_code_used(email)
    return True


def logout(token: str) -> None:
    auth_db.delete_token(token)


# ============ 资料更新 ============
def update_nickname(token: str, nickname: str) -> None:
    user = get_user_by_token(token)
    if not user:
        raise ValueError("未登录")
    auth_db.update_user_nickname(user[0], nickname)


def update_phone(token: str, phone: str, code: str) -> None:
    user = get_user_by_token(token)
    if not user:
        raise ValueError("未登录")
    if not validate_phone(phone):
        raise ValueError("手机号格式不正确")

    stored_code = auth_db.get_valid_phone_code(phone)
    if not stored_code or stored_code != code:
        raise ValueError("验证码错误或已过期")

    if auth_db.phone_exists(phone):
        existing = auth_db.get_user_by_phone(phone)
        if existing and existing[0] != user[0]:
            raise ValueError("手机号已被注册")

    auth_db.update_user_phone(user[0], phone)
    auth_db.mark_phone_code_used(phone)


def update_email(token: str, email: str, code: str) -> None:
    user = get_user_by_token(token)
    if not user:
        raise ValueError("未登录")
    if not validate_email(email):
        raise ValueError("邮箱格式不正确")

    stored_code = auth_db.get_valid_email_code(email)
    if not stored_code or stored_code != code:
        raise ValueError("验证码错误或已过期")

    if auth_db.check_email_exists(email):
        existing = auth_db.get_user_by_email(email)
        if existing and existing[0] != user[0]:
            raise ValueError("邮箱已被注册")

    auth_db.update_user_email(user[0], email)
    auth_db.mark_email_code_used(email)


def update_password(token: str, old_password: str, new_password: str) -> None:
    user = get_user_by_token(token)
    if not user:
        raise ValueError("未登录")
    if len(new_password) < 6:
        raise ValueError("新密码至少6位")

    user_full = auth_db.get_user_by_id(user[0])
    if not user_full:
        raise ValueError("用户不存在")

    if user_full[2] and user_full[2] != "":
        if hash_password(old_password) != user_full[2]:
            raise ValueError("旧密码错误")

    auth_db.update_user_password_by_id(user[0], hash_password(new_password))


def get_user_full_info(token: str) -> dict | None:
    user = get_user_by_token(token)
    if not user:
        return None
    user_full = auth_db.get_user_by_id(user[0])
    if not user_full:
        return None
    return {
        "id": user_full[0],
        "phone": user_full[1],
        "nickname": user_full[3],
        "subscription_level": user_full[4],
        "subscription_expire_at": user_full[5],
        "email": user_full[6],
    }
