"""
auth_code_service.py - 认证基础设施：验证码与工具函数

属于基础设施层，提供：
- 密码哈希、token 生成
- 手机号/邮箱格式校验
- 验证码生成与存储
- 邮件发送
"""
from __future__ import annotations

import hashlib
import random
import re
from datetime import datetime, timedelta

from core.config_service import get_app_name
from core.email_service import send_email
from script.db import auth_db


# ============ 工具函数 ============
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def generate_token() -> str:
    return hashlib.sha256(f"{random.random()}{datetime.now().isoformat()}".encode()).hexdigest()


def validate_phone(phone: str) -> bool:
    return bool(re.fullmatch(r'1[3-9]\d{9}', phone))


def validate_email(email: str) -> bool:
    return bool(re.fullmatch(r'^[\w\.-]+@[\w\.-]+\.\w+$', email))


def generate_code() -> str:
    return str(random.randint(100000, 999999))


# ============ 验证码 ============
def send_phone_code(phone: str) -> str:
    """发送手机验证码，返回验证码"""
    if not validate_phone(phone):
        raise ValueError("手机号格式不正确")
    code = generate_code()
    expire_at = (datetime.now() + timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M:%S")
    auth_db.upsert_phone_code(phone, code, expire_at)
    print(f"[模拟短信] {phone} 验证码: {code}")
    return code


def send_email_code(email: str) -> bool:
    """发送邮箱验证码"""
    if not validate_email(email):
        raise ValueError("邮箱格式不正确")
    if auth_db.check_email_exists(email):
        raise ValueError("邮箱已被注册")
    code = generate_code()
    expire_at = (datetime.now() + timedelta(minutes=15)).strftime("%Y-%m-%d %H:%M:%S")
    auth_db.upsert_email_code(email, code, expire_at)
    ok = send_email(
        email,
        subject=f"您的{get_app_name()}注册验证码",
        body=f"您的注册验证码是：{code}，15分钟内有效，请勿告知他人。",
    )
    if not ok:
        raise ValueError("邮件发送失败，请检查邮箱地址或稍后重试")
    return True


def send_reset_code(email: str) -> bool:
    """发送密码重置验证码"""
    if not validate_email(email):
        raise ValueError("邮箱格式不正确")
    if not auth_db.check_email_exists(email):
        raise ValueError("该邮箱未注册")
    code = generate_code()
    expire_at = (datetime.now() + timedelta(minutes=15)).strftime("%Y-%m-%d %H:%M:%S")
    auth_db.upsert_reset_code(email, code, expire_at)
    ok = send_email(
        email,
        subject=f"您的{get_app_name()}密码重置验证码",
        body=f"您的密码重置验证码是：{code}，15分钟内有效，请勿告知他人。",
    )
    if not ok:
        raise ValueError("邮件发送失败，请检查邮箱地址或稍后重试")
    return True
