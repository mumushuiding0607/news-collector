"""
email_service.py - 统一邮件服务模块

提供邮件发送能力，被 auth_service 等模块调用。
SMTP 配置通过环境变量获取：
  SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD
未配置 SMTP 时打印到控制台（开发/测试用）。
"""
from __future__ import annotations

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from dotenv import load_dotenv

# 加载 backend/.env 到环境变量
_ENV_PATH = Path(__file__).parent.parent / ".env"
load_dotenv(_ENV_PATH, override=False)

# SMTP 配置
_SMTP_HOST = os.environ.get("SMTP_HOST", "")
_SMTP_PORT = int(os.environ.get("SMTP_PORT", 587))
_SMTP_USER = os.environ.get("SMTP_USER", "")
_SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")


def send_email(to_email: str, subject: str, body: str) -> bool:
    """
    通过 SMTP 发送邮件。

    Args:
        to_email: 收件人邮箱
        subject: 邮件主题
        body: 邮件正文（纯文本）

    Returns:
        True 发送成功
        False 发送失败（未配置 SMTP 也返回 False）
    """
    if not _SMTP_HOST or not _SMTP_USER or not _SMTP_PASSWORD:
        print(f"[邮件] 未配置 SMTP（HOST={_SMTP_HOST}, USER={_SMTP_USER}），无法发送")
        return False
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