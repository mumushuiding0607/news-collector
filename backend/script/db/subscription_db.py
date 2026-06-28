"""
subscription_db.py - 订阅相关的数据库 CRUD

封装 subscription_records 表的操作和订阅激活事务。
封装 orders 表的 CRUD（订单与订阅流程紧密相关）。
"""
from __future__ import annotations
from datetime import datetime
from script.db import get_conn, put_conn


def cancel_active_subscription(user_id: int) -> None:
    """取消用户当前生效的订阅"""
    conn = get_conn()
    try:
        conn.execute(
            "UPDATE subscription_records SET status = 'cancelled' "
            "WHERE user_id = ? AND status = 'active'",
            (user_id,),
        )
        conn.commit()
    finally:
        put_conn(conn)


def cancel_subscription_full(user_id: int) -> None:
    """取消用户订阅（subscription_records + auth_users）"""
    conn = get_conn()
    try:
        conn.execute(
            "UPDATE subscription_records SET status = 'cancelled' "
            "WHERE user_id = ? AND status = 'active'",
            (user_id,),
        )
        conn.execute(
            "UPDATE auth_users SET subscription_level = 'free', subscription_expire_at = NULL WHERE id = ?",
            (user_id,),
        )
        conn.commit()
    finally:
        put_conn(conn)


def activate_subscription(user_id: int, level: str, price: float, start_at: datetime, end_at: datetime) -> int:
    """
    激活订阅（事务性）：
    1. 取消当前生效订阅
    2. 插入新订阅记录
    3. 更新用户订阅状态
    返回 subscription_record id
    """
    conn = get_conn()
    try:
        # 取消旧订阅
        conn.execute(
            "UPDATE subscription_records SET status = 'cancelled' "
            "WHERE user_id = ? AND status = 'active'",
            (user_id,),
        )
        # 插入新订阅记录
        cursor = conn.execute(
            "INSERT INTO subscription_records (user_id, level, price, start_at, end_at, status) "
            "VALUES (?, ?, ?, ?, ?, 'active')",
            (user_id, level, price, start_at.strftime("%Y-%m-%d %H:%M:%S"),
             end_at.strftime("%Y-%m-%d %H:%M:%S")),
        )
        # 更新用户订阅状态
        conn.execute(
            "UPDATE auth_users SET subscription_level = ?, subscription_expire_at = ? "
            "WHERE id = ?",
            (level, end_at.strftime("%Y-%m-%d %H:%M:%S"), user_id),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        put_conn(conn)


def get_active_subscription(user_id: int) -> tuple | None:
    """获取用户当前生效订阅"""
    conn = get_conn()
    try:
        return conn.execute(
            "SELECT id, user_id, level, price, start_at, end_at, status "
            "FROM subscription_records "
            "WHERE user_id = ? AND status = 'active'",
            (user_id,),
        ).fetchone()
    finally:
        put_conn(conn)


def mark_order_expired(order_no: str) -> None:
    """标记订单过期"""
    conn = get_conn()
    try:
        conn.execute(
            "UPDATE orders SET status = 'expired' WHERE order_no = ? AND status = 'pending'",
            (order_no,),
        )
        conn.commit()
    finally:
        put_conn(conn)


def activate_subscription_pending(user_id: int, level: str, price: float, start_at: datetime, end_at: datetime) -> int:
    """
    激活订阅（待确认状态，用户转账后直接生效，但 admin 需确认）：
    1. 取消当前生效订阅
    2. 插入新订阅记录（status=pending_confirm）
    3. 更新用户订阅状态
    返回 subscription_record id
    """
    conn = get_conn()
    try:
        conn.execute(
            "UPDATE subscription_records SET status = 'cancelled' "
            "WHERE user_id = ? AND status = 'active'",
            (user_id,),
        )
        cursor = conn.execute(
            "INSERT INTO subscription_records (user_id, level, price, start_at, end_at, status) "
            "VALUES (?, ?, ?, ?, ?, 'pending_confirm')",
            (user_id, level, price, start_at.strftime("%Y-%m-%d %H:%M:%S"),
             end_at.strftime("%Y-%m-%d %H:%M:%S")),
        )
        conn.execute(
            "UPDATE auth_users SET subscription_level = ?, subscription_expire_at = ? "
            "WHERE id = ?",
            (level, end_at.strftime("%Y-%m-%d %H:%M:%S"), user_id),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        put_conn(conn)


# ============ orders（订单表）============


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
    """创建订单，返回 order id"""
    conn = get_conn()
    try:
        cur = conn.execute(
            "INSERT INTO orders (order_no, user_id, level, amount, pay_method, expire_at, wechat_code_url, wechat_prepay_id) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (order_no, user_id, level, amount, pay_method, expire_at, wechat_code_url, wechat_prepay_id),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        put_conn(conn)


def get_order(order_no: str) -> tuple | None:
    """通过订单号获取订单详情"""
    conn = get_conn()
    try:
        return conn.execute(
            "SELECT id, order_no, user_id, level, amount, pay_method, status, trade_no, "
            "wechat_prepay_id, wechat_code_url, created_at, updated_at, expire_at "
            "FROM orders WHERE order_no = ?",
            (order_no,),
        ).fetchone()
    finally:
        put_conn(conn)


def update_order_paid(order_no: str, trade_no: str) -> None:
    """更新订单为已支付"""
    conn = get_conn()
    try:
        conn.execute(
            "UPDATE orders SET status = 'paid', trade_no = ?, updated_at = datetime('now','localtime') "
            "WHERE order_no = ?",
            (trade_no, order_no),
        )
        conn.commit()
    finally:
        put_conn(conn)


def get_orders_by_user(user_id: int, limit: int = 20) -> list:
    """获取用户的订单历史"""
    conn = get_conn()
    try:
        return conn.execute(
            "SELECT id, order_no, level, amount, pay_method, status, trade_no, "
            "created_at, expire_at "
            "FROM orders WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    finally:
        put_conn(conn)