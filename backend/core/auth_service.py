"""
auth_service.py - 认证模块统一导出层

保留向后兼容，现有 import 不受影响。
实际实现已拆分到：
  core/auth_code_service.py  - 验证码与工具函数
  core/auth_biz_service.py   - 业务逻辑层
"""
from core.auth_code_service import (
    hash_password,
    generate_token,
    validate_phone,
    validate_email,
    generate_code,
    send_phone_code,
    send_email_code,
    send_reset_code,
)
from core.auth_biz_service import (
    get_user_by_token,
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
)