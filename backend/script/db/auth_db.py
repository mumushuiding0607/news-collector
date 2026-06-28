"""
auth_db.py - 用户认证数据库访问层

所有 auth_users、auth_codes、email_codes、reset_codes、auth_tokens、login_attempts
的 CRUD 必须通过此模块，禁止在 api/ 中直接写 SQL。

使用：
    from script.db import auth_db
    auth_db.create_user(phone="...", password_hash="...", email=None)
"""

from datetime import datetime

from script.db import get_conn, put_conn

# orders 表的操作委托给 subscription_db（保持接口兼容）
from script.db.subscription_db import (
    create_order as _create_order_sub,
    get_order as _get_order_sub,
    update_order_paid as _update_order_paid_sub,
    get_orders_by_user as _get_orders_by_user_sub,
)


# ============ orders（委托给 subscription_db）============
def create_order(
    order_no: str,
    user_id: int,
    level: str,
    amount: float,
    pay_method: str,
    expire_at: str,
    wechat_code_url: str | None = None,
    wechat_prepay_id: str | None = None,
) -> int:
    """创建订单，返回 order id（委托给 subscription_db）"""
    return _create_order_sub(order_no, user_id, level, amount, pay_method, expire_at, wechat_code_url, wechat_prepay_id)


def get_order(order_no: str) -> tuple | None:
    """通过订单号获取订单详情（委托给 subscription_db）"""
    return _get_order_sub(order_no)


def update_order_paid(order_no: str, trade_no: str) -> None:
    """更新订单为已支付（委托给 subscription_db）"""
    _update_order_paid_sub(order_no, trade_no)


def get_orders_by_user(user_id: int, limit: int = 20) -> list:
    """获取用户的订单历史（委托给 subscription_db）"""
    return _get_orders_by_user_sub(user_id, limit)

__all__ = [
    # auth_codes（手机验证码）
    "upsert_phone_code",
    "get_valid_phone_code",
    "mark_phone_code_used",
    # email_codes（邮箱验证码）
    "upsert_email_code",
    "get_valid_email_code",
    "mark_email_code_used",
    "check_email_exists",
    # reset_codes（密码重置验证码）
    "upsert_reset_code",
    "get_valid_reset_code",
    "mark_reset_code_used",
    # auth_users
    "get_user_by_phone",
    "get_user_by_email",
    "get_user_by_id",
    "create_user",
    "update_user_password_by_email",
    "update_user_nickname",
    "update_user_email",
    "update_user_phone",
    "phone_exists",
    # auth_tokens
    "create_token",
    "get_user_by_token",
    "delete_token",
    # login_attempts
    "is_login_locked",
    "record_login_attempt",
    "lock_phone",
    # orders（委托给 subscription_db）
    "create_order",
    "get_order",
    "update_order_paid",
    "get_orders_by_user",
]


# ============ auth_codes（手机验证码）============


def upsert_phone_code(phone: str, code: str, expire_at: str) -> None:
    """手机验证码：标记旧码已用，插入新码"""
    conn = get_conn()
    try:
        conn.execute(
            "UPDATE auth_codes SET used = 1 WHERE phone = ? AND used = 0", (phone,)
        )
        conn.execute(
            "INSERT INTO auth_codes (phone, code, expire_at) VALUES (?, ?, ?)",
            (phone, code, expire_at),
        )
        conn.commit()
    finally:
        put_conn(conn)


def get_valid_phone_code(phone: str) -> str | None:
    """获取手机有效验证码，，返回 code 字符串或 None"""
    conn = get_conn()
    try:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row = conn.execute(
            "SELECT code FROM auth_codes WHERE phone = ? AND used = 0 AND expire_at > ? "
            "ORDER BY id DESC LIMIT 1",
            (phone, now),
        ).fetchone()
        return row[0] if row else None
    finally:
        put_conn(conn)


def mark_phone_code_used(phone: str) -> None:
    """标记该手机号的所有可用验证码为已用"""
    conn = get_conn()
    try:
        conn.execute("UPDATE auth_codes SET used = 1 WHERE phone = ?", (phone,))
        conn.commit()
    finally:
        put_conn(conn)


# ============ email_codes（邮箱验证码）============


def upsert_email_code(email: str, code: str, expire_at: str) -> None:
    """邮箱验证码：标记旧码已用，插入新码"""
    conn = get_conn()
    try:
        conn.execute(
            "UPDATE email_codes SET used = 1 WHERE email = ? AND used = 0", (email,)
        )
        conn.execute(
            "INSERT INTO email_codes (email, code, expire_at) VALUES (?, ?, ?)",
            (email, code, expire_at),
        )
        conn.commit()
    finally:
        put_conn(conn)


def get_valid_email_code(email: str) -> str | None:
    """获取邮箱有效验证码，返回 code 字符串或 None"""
    conn = get_conn()
    try:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row = conn.execute(
            "SELECT code FROM email_codes WHERE email = ? AND used = 0 AND expire_at > ? "
            "ORDER BY id DESC LIMIT 1",
            (email, now),
        ).fetchone()
        return row[0] if row else None
    finally:
        put_conn(conn)


def mark_email_code_used(email: str) -> None:
    """标记该邮箱的所有可用验证码为已用"""
    conn = get_conn()
    try:
        conn.execute("UPDATE email_codes SET used = 1 WHERE email = ?", (email,))
        conn.commit()
    finally:
        put_conn(conn)


def check_email_exists(email: str) -> bool:
    """检查邮箱是否已在 auth_users 中注册"""
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT id FROM auth_users WHERE email = ?", (email,)
        ).fetchone()
        return row is not None
    finally:
        put_conn(conn)


# ============ reset_codes（密码重置验证码）============


def upsert_reset_code(email: str, code: str, expire_at: str) -> None:
    """密码重置验证码：插入新码（不清除旧码，保留历史）"""
    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO reset_codes (email, code, expire_at) VALUES (?, ?, ?)",
            (email, code, expire_at),
        )
        conn.commit()
    finally:
        put_conn(conn)


def get_valid_reset_code(email: str) -> str | None:
    """获取密码重置有效验证码，返回 code 字符串或 None"""
    conn = get_conn()
    try:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row = conn.execute(
            "SELECT code FROM reset_codes WHERE email = ? AND used = 0 AND expire_at > ? "
            "ORDER BY id DESC LIMIT 1",
            (email, now),
        ).fetchone()
        return row[0] if row else None
    finally:
        put_conn(conn)


def mark_reset_code_used(email: str) -> None:
    """标记该邮箱的所有密码重置验证码为已用"""
    conn = get_conn()
    try:
        conn.execute("UPDATE reset_codes SET used = 1 WHERE email = ?", (email,))
        conn.commit()
    finally:
        put_conn(conn)


# ============ auth_users（用户表）============


def phone_exists(phone: str) -> bool:
    """检查手机号是否已注册"""
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT id FROM auth_users WHERE phone = ?", (phone,)
        ).fetchone()
        return row is not None
    finally:
        put_conn(conn)


def get_user_by_phone(phone: str) -> tuple | None:
    """通过手机号获取用户，返回 (id, phone, password_hash, nickname, subscription_level, subscription_expire_at) 或 None"""
    conn = get_conn()
    try:
        return conn.execute(
            "SELECT id, phone, password_hash, nickname, subscription_level, subscription_expire_at "
            "FROM auth_users WHERE phone = ?",
            (phone,),
        ).fetchone()
    finally:
        put_conn(conn)


def get_user_by_email(email: str) -> tuple | None:
    """通过邮箱获取用户，返回 (id, phone, password_hash, nickname, subscription_level, subscription_expire_at) 或 None"""
    conn = get_conn()
    try:
        return conn.execute(
            "SELECT id, phone, password_hash, nickname, subscription_level, subscription_expire_at "
            "FROM auth_users WHERE email = ?",
            (email,),
        ).fetchone()
    finally:
        put_conn(conn)


def create_user(
    phone: str | None, password_hash: str, email: str | None
) -> int:
    """创建用户，返回 user_id"""
    conn = get_conn()
    try:
        cur = conn.execute(
            "INSERT INTO auth_users (phone, password_hash, email, subscription_level) "
            "VALUES (?, ?, ?, 'free')",
            (phone, password_hash, email),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        put_conn(conn)


def update_user_password_by_email(email: str, password_hash: str) -> None:
    """通过邮箱更新用户密码"""
    conn = get_conn()
    try:
        conn.execute(
            "UPDATE auth_users SET password_hash = ? WHERE email = ?",
            (password_hash, email),
        )
        conn.commit()
    finally:
        put_conn(conn)


def update_user_password_by_id(user_id: int, password_hash: str) -> None:
    """通过用户ID更新密码"""
    conn = get_conn()
    try:
        conn.execute(
            "UPDATE auth_users SET password_hash = ? WHERE id = ?",
            (password_hash, user_id),
        )
        conn.commit()
    finally:
        put_conn(conn)


# ============ auth_tokens（登录令牌）============


def create_token(user_id: int, token: str) -> None:
    """创建登录令牌"""
    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO auth_tokens (user_id, token) VALUES (?, ?)",
            (user_id, token),
        )
        conn.commit()
    finally:
        put_conn(conn)


def get_user_by_token(token: str) -> tuple | None:
    """通过 token 获取用户信息，返回 (id, phone, email, nickname, subscription_level, subscription_expire_at) 或 None"""
    conn = get_conn()
    try:
        return conn.execute(
            "SELECT u.id, u.phone, u.email, u.nickname, u.subscription_level, u.subscription_expire_at "
            "FROM auth_tokens t JOIN auth_users u ON t.user_id = u.id WHERE t.token = ?",
            (token,),
        ).fetchone()
    finally:
        put_conn(conn)


def delete_token(token: str) -> None:
    """删除令牌（登出）"""
    conn = get_conn()
    try:
        conn.execute("DELETE FROM auth_tokens WHERE token = ?", (token,))
        conn.commit()
    finally:
        put_conn(conn)


# ============ login_attempts（频率限制）============


def is_login_locked(phone: str) -> bool:
    """检查手机号是否被锁定（5次失败后锁5分钟）"""
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT attempt_count, locked_until FROM login_attempts WHERE phone = ?",
            (phone,),
        ).fetchone()
        if not row:
            return False
        attempt_count, locked_until = row
        if locked_until and datetime.strptime(locked_until, "%Y-%m-%d %H:%M:%S") > datetime.now():
            return True
        if attempt_count >= 5:
            return True
        return False
    finally:
        put_conn(conn)


def record_login_attempt(phone: str, success: bool) -> None:
    """记录登录尝试结果"""
    conn = get_conn()
    try:
        if success:
            conn.execute("DELETE FROM login_attempts WHERE phone = ?", (phone,))
        else:
            row = conn.execute(
                "SELECT attempt_count FROM login_attempts WHERE phone = ?", (phone,)
            ).fetchone()
            if row:
                conn.execute(
                    "UPDATE login_attempts SET attempt_count = attempt_count + 1 WHERE phone = ?",
                    (phone,),
                )
            else:
                conn.execute(
                    "INSERT INTO login_attempts (phone, attempt_count) VALUES (?, 1)",
                    (phone,),
                )
        conn.commit()
    finally:
        put_conn(conn)


def lock_phone(phone: str, locked_until: str) -> None:
    """锁定手机号"""
    conn = get_conn()
    try:
        conn.execute(
            "UPDATE login_attempts SET locked_until = ?, attempt_count = 0 WHERE phone = ?",
            (locked_until, phone),
        )
        conn.commit()
    finally:
        put_conn(conn)


def get_user_by_id(user_id: int) -> tuple | None:
    """通过用户ID获取用户，返回 (id, phone, password_hash, nickname, subscription_level, subscription_expire_at, email) 或 None"""
    conn = get_conn()
    try:
        return conn.execute(
            "SELECT id, phone, password_hash, nickname, subscription_level, subscription_expire_at, email "
            "FROM auth_users WHERE id = ?",
            (user_id,),
        ).fetchone()
    finally:
        put_conn(conn)


def update_user_nickname(user_id: int, nickname: str) -> None:
    """更新用户昵称"""
    conn = get_conn()
    try:
        conn.execute(
            "UPDATE auth_users SET nickname = ?, updated_at = datetime('now','localtime') WHERE id = ?",
            (nickname, user_id),
        )
        conn.commit()
    finally:
        put_conn(conn)


def update_user_email(user_id: int, email: str) -> None:
    """更新用户邮箱"""
    conn = get_conn()
    try:
        conn.execute(
            "UPDATE auth_users SET email = ?, updated_at = datetime('now','localtime') WHERE id = ?",
            (email, user_id),
        )
        conn.commit()
    finally:
        put_conn(conn)


def update_user_phone(user_id: int, phone: str) -> None:
    """更新用户手机号"""
    conn = get_conn()
    try:
        conn.execute(
            "UPDATE auth_users SET phone = ?, updated_at = datetime('now','localtime') WHERE id = ?",
            (phone, user_id),
        )
        conn.commit()
    finally:
        put_conn(conn)