"""
auth_tools.py - Auth 业务工具函数

包含：密码哈希、Token 生成、验证码生成、手机邮箱校验、邮件发送
"""

import hashlib
import os
import random
import re
import smtplib
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def generate_token() -> str:
    return hashlib.sha256(f"{random.random()}{datetime.now().isoformat()}".encode()).hexdigest()


def generate_code() -> str:
    return str(random.randint(100000, 999999))


def validate_phone(phone: str) -> bool:
    return bool(re.fullmatch(r'1[3-9]\d{9}', phone))


def validate_email(email: str) -> bool:
    return bool(re.fullmatch(r'^[\w\.-]+@[\w\.-]+\.\w+$', email))


_SMTP_HOST = os.environ.get("SMTP_HOST", "")
_SMTP_PORT = int(os.environ.get("SMTP_PORT", 587))
_SMTP_USER = os.environ.get("SMTP_USER", "")
_SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")


def send_email(to_email: str, subject: str, body: str) -> bool:
    """通过 QQ SMTP 发送邮件，未配置则打印到控制台。"""
    if not _SMTP_USER or not _SMTP_PASSWORD:
        print(f"[邮件] 未配置 SMTP，模拟发送 -> {to_email}: {subject}")
        return True
    try:
        msg = MIMEMultipart()
        msg["From"] = _SMTP_USER
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))
        with smtplib.SMTP(_SMTP_HOST, _SMTP_PORT, timeout=10) as server:
            server.starttls()
            server.login(_SMTP_USER, _SMTP_PASSWORD)
            server.sendmail(_SMTP_USER, [to_email], msg.as_string())
        print(f"[邮件] 已发送至 {to_email}: {subject}")
        return True
    except Exception as e:
        print(f"[邮件] 发送失败: {e}")
        return False