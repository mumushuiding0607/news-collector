"""
auth_models.py - Auth 相关 Pydantic 模型
"""

from typing import Optional
from pydantic import BaseModel


class SendPhoneCodeRequest(BaseModel):
    phone: str


class SendEmailCodeRequest(BaseModel):
    email: str


class SendCodeRequest(BaseModel):
    phone: Optional[str] = None
    email: Optional[str] = None


class LoginCodeRequest(BaseModel):
    phone: str
    code: str


class LoginPasswordRequest(BaseModel):
    email: str
    password: str


class RegisterRequest(BaseModel):
    phone: str | None = None
    password: str | None = None
    email: str | None = None


class PhoneRegisterRequest(BaseModel):
    phone: str
    password: str


class SendResetCodeRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    email: str
    code: str
    new_password: str


class EmailRegisterRequest(BaseModel):
    email: str
    code: str
    password: str


class UserResponse(BaseModel):
    id: int
    phone: str | None
    email: str | None
    nickname: str | None
    subscription_level: str
    subscription_expire_at: str | None


class AuthResponse(BaseModel):
    token: str
    user: UserResponse


class UpdateNicknameRequest(BaseModel):
    nickname: str


class UpdatePhoneRequest(BaseModel):
    phone: str
    code: str


class UpdateEmailRequest(BaseModel):
    email: str
    code: str


class UpdatePasswordRequest(BaseModel):
    old_password: str
    new_password: str