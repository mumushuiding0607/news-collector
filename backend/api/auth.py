"""
Auth API - 用户登录注册

只负责路由和参数校验，业务逻辑委托给 core.auth_service。
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from .auth_models import (
    SendCodeRequest,
    LoginCodeRequest,
    LoginPasswordRequest,
    PhoneRegisterRequest,
    EmailRegisterRequest,
    SendResetCodeRequest,
    ResetPasswordRequest,
    UpdateNicknameRequest,
    UpdatePhoneRequest,
    UpdateEmailRequest,
    UpdatePasswordRequest,
    AuthResponse,
    UserResponse,
)
from core.auth_service import (
    send_phone_code,
    send_email_code,
    send_reset_code,
    register_by_phone,
    login_by_phone_code,
    login_by_password,
    email_register,
    reset_password,
    logout,
    update_nickname,
    update_phone,
    update_email,
    update_password,
    get_user_full_info,
    get_user_by_token,
    validate_email as val_email,
)
from script.db import auth_db

router = APIRouter(prefix="/auth", tags=["认证"])


def _build_auth_response(token: str, user_id: int, phone: str | None = None, email: str | None = None) -> AuthResponse:
    """构建 AuthResponse，消除重复的 UserResponse 构造"""
    return AuthResponse(
        token=token,
        user=UserResponse(
            id=user_id,
            phone=phone,
            email=email,
            nickname=None,
            subscription_level="free",
            subscription_expire_at=None,
        ),
    )


# ============ 路由 ============
@router.post("/send_code")
def send_code(req: SendCodeRequest):
    if req.phone is not None:
        try:
            code = send_phone_code(req.phone)
            return {"success": True, "message": "验证码已发送", "code": code}
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    if req.email is not None:
        try:
            send_email_code(req.email)
            return {"success": True, "message": "验证码已发送"}
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    raise HTTPException(status_code=400, detail="phone 或 email 参数必填其一")


@router.post("/register", response_model=AuthResponse)
def register(req: PhoneRegisterRequest):
    """手机号注册（密码方式，无需验证码）"""
    try:
        token, user_id = register_by_phone(req.phone, req.password)
        return _build_auth_response(token, user_id, phone=req.phone)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/email_register", response_model=AuthResponse)
def email_register_api(req: EmailRegisterRequest):
    """邮箱注册（需先通过 /send_code 发送验证码）"""
    try:
        token, user_id = email_register(req.email, req.code, req.password)
        return _build_auth_response(token, user_id, email=req.email)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login_code", response_model=AuthResponse)
def login_code(req: LoginCodeRequest):
    try:
        token, user_id = login_by_phone_code(req.phone, req.code)
        return _build_auth_response(token, user_id, phone=req.phone)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login_password", response_model=AuthResponse)
def login_password(req: LoginPasswordRequest):
    try:
        token, user_row = login_by_password(req.email, req.password)
        return AuthResponse(
            token=token,
            user=UserResponse(
                id=user_row[0],
                phone=user_row[1],
                email=user_row[2],
                nickname=user_row[3],
                subscription_level=user_row[4],
                subscription_expire_at=user_row[5],
            ),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/current_user")
def current_user(request: Request):
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not token:
        return {"isLoggedIn": False}
    user_row = get_user_by_token(token)
    if not user_row:
        return {"isLoggedIn": False}
    return {
        "isLoggedIn": True,
        "user": {
            "id": user_row[0],
            "phone": user_row[1],
            "email": user_row[2],
            "nickname": user_row[3],
            "subscriptionLevel": user_row[4],
            "subscription_expire_at": user_row[5],
        },
    }


@router.post("/logout")
def logout_api(request: Request):
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    logout(token)
    return {"success": True}


@router.post("/send_reset_code")
def send_reset_code_api(req: SendResetCodeRequest):
    try:
        send_reset_code(req.email)
        return {"success": True, "message": "验证码已发送"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/reset_password")
def reset_password_api(req: ResetPasswordRequest):
    try:
        reset_password(req.email, req.code, req.new_password)
        return {"success": True, "message": "密码重置成功"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/check_email")
def check_email(email: str):
    if not val_email(email):
        raise HTTPException(status_code=400, detail="邮箱格式不正确")
    return {"exists": auth_db.check_email_exists(email)}


@router.get("/user_info")
def user_info(request: Request):
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    info = get_user_full_info(token)
    if not info:
        raise HTTPException(status_code=401, detail="未登录")
    return info


@router.put("/update_nickname")
def update_nickname_api(req: UpdateNicknameRequest, request: Request):
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    try:
        update_nickname(token, req.nickname)
        return {"success": True, "message": "昵称已更新"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/update_phone")
def update_phone_api(req: UpdatePhoneRequest, request: Request):
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    try:
        update_phone(token, req.phone, req.code)
        return {"success": True, "message": "手机号已更新"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/update_email")
def update_email_api(req: UpdateEmailRequest, request: Request):
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    try:
        update_email(token, req.email, req.code)
        return {"success": True, "message": "邮箱已更新"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/update_password")
def update_password_api(req: UpdatePasswordRequest, request: Request):
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    try:
        update_password(token, req.old_password, req.new_password)
        return {"success": True, "message": "密码已更新"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))