"""
Auth API - 用户登录注册
"""
import sys
import hashlib
import random
import re
from datetime import datetime, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "script"))

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from common.db.connection import get_conn, init_db

router = APIRouter(prefix="/auth", tags=["认证"])
init_db()


# ============ 模型 ============
class SendCodeRequest(BaseModel):
    phone: str


class LoginCodeRequest(BaseModel):
    phone: str
    code: str


class LoginPasswordRequest(BaseModel):
    phone: str
    password: str


class RegisterRequest(BaseModel):
    phone: str
    password: str
    email: str = ""
    code: str = ""


class SendResetCodeRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    email: str
    code: str
    new_password: str


class UserResponse(BaseModel):
    id: int
    phone: str
    nickname: str | None
    subscription_level: str
    subscription_expire_at: str | None


class AuthResponse(BaseModel):
    token: str
    user: UserResponse


# ============ 工具函数 ============
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, hashed: str) -> bool:
    return hashlib.sha256(password.encode()).hexdigest() == hashed


def generate_token() -> str:
    return hashlib.sha256(f"{random.random()}{datetime.now().isoformat()}".encode()).hexdigest()


def validate_phone(phone: str) -> bool:
    return bool(re.fullmatch(r'1[3-9]\d{9}', phone))


def validate_email(email: str) -> bool:
    return bool(re.fullmatch(r'^[\w\.-]+@[\w\.-]+\.\w+$', email))


def generate_code() -> str:
    return str(random.randint(100000, 999999))


def get_user_from_token(token: str, conn):
    row = conn.execute(
        "SELECT u.id, u.phone, u.nickname, u.subscription_level, u.subscription_expire_at "
        "FROM auth_tokens t JOIN auth_users u ON t.user_id = u.id WHERE t.token = ?",
        (token,)
    ).fetchone()
    return row


def _check_rate_limit(phone: str, conn) -> None:
    """检查登录频率限制，5次失败后锁5分钟"""
    row = conn.execute(
        "SELECT attempt_count, locked_until FROM login_attempts WHERE phone = ?",
        (phone,)
    ).fetchone()
    if row:
        if row[1] and datetime.strptime(row[1], "%Y-%m-%d %H:%M:%S") > datetime.now():
            raise HTTPException(status_code=429, detail="登录次数过多，请5分钟后再试")
        if row[0] >= 5:
            locked = (datetime.now() + timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S")
            conn.execute(
                "UPDATE login_attempts SET locked_until = ?, attempt_count = 0 WHERE phone = ?",
                (locked, phone)
            )
            conn.commit()
            raise HTTPException(status_code=429, detail="登录次数过多，请5分钟后再试")


def _record_attempt(phone: str, success: bool, conn) -> None:
    if success:
        conn.execute("DELETE FROM login_attempts WHERE phone = ?", (phone,))
        conn.commit()
    else:
        row = conn.execute("SELECT attempt_count FROM login_attempts WHERE phone = ?", (phone,)).fetchone()
        if row:
            conn.execute(
                "UPDATE login_attempts SET attempt_count = attempt_count + 1 WHERE phone = ?",
                (phone,)
            )
        else:
            conn.execute(
                "INSERT INTO login_attempts (phone, attempt_count) VALUES (?, 1)",
                (phone,)
            )
        conn.commit()


# ============ 路由 ============
@router.post("/send_code")
def send_code(req: SendCodeRequest):
    """发送短信验证码"""
    if not validate_phone(req.phone):
        raise HTTPException(status_code=400, detail="手机号格式不正确")

    code = generate_code()
    expire_at = (datetime.now() + timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M:%S")

    conn = get_conn()
    try:
        conn.execute("UPDATE auth_codes SET used = 1 WHERE phone = ? AND used = 0", (req.phone,))
        conn.execute("INSERT INTO auth_codes (phone, code, expire_at) VALUES (?, ?, ?)",
                     (req.phone, code, expire_at))
        conn.commit()
        print(f"[模拟短信] {req.phone} 验证码: {code}")
        return {"success": True, "message": "验证码已发送", "code": code}
    finally:
        conn.close()


@router.post("/register", response_model=AuthResponse)
def register(req: RegisterRequest):
    """注册账号（密码模式：手机+密码，无需验证码）"""
    if not validate_phone(req.phone):
        raise HTTPException(status_code=400, detail="手机号格式不正确")
    if len(req.password) < 6:
        raise HTTPException(status_code=400, detail="密码至少6位")
    if req.email and not validate_email(req.email):
        raise HTTPException(status_code=400, detail="邮箱格式不正确")

    conn = get_conn()
    try:
        exist = conn.execute("SELECT id FROM auth_users WHERE phone = ?", (req.phone,)).fetchone()
        if exist:
            raise HTTPException(status_code=400, detail="手机号已注册")

        password_hash = hash_password(req.password)
        cur = conn.execute(
            "INSERT INTO auth_users (phone, password_hash, subscription_level) VALUES (?, ?, 'free')",
            (req.phone, password_hash)
        )
        conn.commit()
        user_id = cur.lastrowid

        token = generate_token()
        conn.execute("INSERT INTO auth_tokens (user_id, token) VALUES (?, ?)", (user_id, token))
        conn.commit()

        _record_attempt(req.phone, True, conn)
        return AuthResponse(
            token=token,
            user=UserResponse(
                id=user_id, phone=req.phone, nickname=None,
                subscription_level="free", subscription_expire_at=None,
            )
        )
    finally:
        conn.close()


@router.post("/login_code", response_model=AuthResponse)
def login_code(req: LoginCodeRequest):
    """验证码登录（用户不存在则自动注册）"""
    if not validate_phone(req.phone):
        raise HTTPException(status_code=400, detail="手机号格式不正确")

    conn = get_conn()
    try:
        _check_rate_limit(req.phone, conn)

        row = conn.execute(
            "SELECT code FROM auth_codes WHERE phone = ? AND used = 0 AND expire_at > ? ORDER BY id DESC LIMIT 1",
            (req.phone, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        ).fetchone()

        if not row or row[0] != req.code:
            _record_attempt(req.phone, False, conn)
            raise HTTPException(status_code=400, detail="验证码错误或已过期")

        # 自动注册：用户不存在则创建
        user_row = conn.execute(
            "SELECT id, phone, nickname, subscription_level, subscription_expire_at FROM auth_users WHERE phone = ?",
            (req.phone,)
        ).fetchone()

        if not user_row:
            # 自动注册，密码为空（仅验证码登录）
            cur = conn.execute(
                "INSERT INTO auth_users (phone, subscription_level) VALUES (?, 'free')",
                (req.phone,)
            )
            conn.commit()
            user_id = cur.lastrowid
        else:
            user_id = user_row[0]

        conn.execute("UPDATE auth_codes SET used = 1 WHERE phone = ?", (req.phone,))
        token = generate_token()
        conn.execute("INSERT INTO auth_tokens (user_id, token) VALUES (?, ?)", (user_id, token))
        conn.commit()

        _record_attempt(req.phone, True, conn)
        return AuthResponse(
            token=token,
            user=UserResponse(
                id=user_id, phone=req.phone, nickname=None,
                subscription_level="free", subscription_expire_at=None,
            )
        )
    finally:
        conn.close()


@router.post("/login_password", response_model=AuthResponse)
def login_password(req: LoginPasswordRequest):
    """密码登录"""
    if not validate_phone(req.phone):
        raise HTTPException(status_code=400, detail="手机号格式不正确")

    conn = get_conn()
    try:
        _check_rate_limit(req.phone, conn)

        user_row = conn.execute(
            "SELECT id, phone, password_hash, nickname, subscription_level, subscription_expire_at "
            "FROM auth_users WHERE phone = ?", (req.phone,)
        ).fetchone()

        if not user_row:
            _record_attempt(req.phone, False, conn)
            raise HTTPException(status_code=404, detail="用户不存在")

        if not user_row[2]:
            _record_attempt(req.phone, False, conn)
            raise HTTPException(status_code=400, detail="请先使用验证码登录")

        if not verify_password(req.password, user_row[2]):
            _record_attempt(req.phone, False, conn)
            raise HTTPException(status_code=401, detail="密码错误")

        token = generate_token()
        conn.execute("INSERT INTO auth_tokens (user_id, token) VALUES (?, ?)", (user_row[0], token))
        conn.commit()

        _record_attempt(req.phone, True, conn)
        return AuthResponse(
            token=token,
            user=UserResponse(
                id=user_row[0], phone=user_row[1], nickname=user_row[3],
                subscription_level=user_row[4], subscription_expire_at=user_row[5],
            )
        )
    finally:
        conn.close()


@router.get("/current_user")
def current_user(request: Request):
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not token:
        return {"isLoggedIn": False}

    conn = get_conn()
    try:
        user_row = get_user_from_token(token, conn)
        if not user_row:
            return {"isLoggedIn": False}
        return {
            "isLoggedIn": True,
            "id": user_row[0], "phone": user_row[1], "nickname": user_row[2],
            "subscriptionLevel": user_row[3], "subscription_expire_at": user_row[4],
        }
    finally:
        conn.close()


@router.post("/logout")
def logout(request: Request):
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not token:
        return {"success": True}
    conn = get_conn()
    try:
        conn.execute("DELETE FROM auth_tokens WHERE token = ?", (token,))
        conn.commit()
        return {"success": True}
    finally:
        conn.close()


# ============ 密码找回 ============
@router.post("/send_reset_code")
def send_reset_code(req: SendResetCodeRequest):
    """发送密码重置验证码（模拟，实际发邮件）"""
    if not validate_email(req.email):
        raise HTTPException(status_code=400, detail="邮箱格式不正确")

    conn = get_conn()
    try:
        user = conn.execute(
            "SELECT id FROM auth_users WHERE email = ?", (req.email,)
        ).fetchone()
        if not user:
            # 不透露用户是否存在
            return {"success": True, "message": "如果邮箱正确，将收到验证码"}

        code = generate_code()
        expire = (datetime.now() + timedelta(minutes=15)).strftime("%Y-%m-%d %H:%M:%S")
        conn.execute(
            "INSERT INTO reset_codes (email, code, expire_at) VALUES (?, ?, ?)",
            (req.email, code, expire)
        )
        conn.commit()
        print(f"[模拟重置密码邮件] {req.email} 验证码: {code}")
        return {"success": True, "message": "验证码已发送", "code": code}
    finally:
        conn.close()


@router.post("/reset_password")
def reset_password(req: ResetPasswordRequest):
    """重置密码"""
    if not validate_email(req.email):
        raise HTTPException(status_code=400, detail="邮箱格式不正确")
    if len(req.new_password) < 6:
        raise HTTPException(status_code=400, detail="密码至少6位")

    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT code FROM reset_codes WHERE email = ? AND used = 0 AND expire_at > ? ORDER BY id DESC LIMIT 1",
            (req.email, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        ).fetchone()

        if not row or row[0] != req.code:
            raise HTTPException(status_code=400, detail="验证码错误或已过期")

        user = conn.execute("SELECT id FROM auth_users WHERE email = ?", (req.email,)).fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")

        conn.execute("UPDATE auth_users SET password_hash = ? WHERE email = ?",
                     (hash_password(req.new_password), req.email))
        conn.execute("UPDATE reset_codes SET used = 1 WHERE email = ?", (req.email,))
        conn.commit()
        return {"success": True, "message": "密码重置成功"}
    finally:
        conn.close()
