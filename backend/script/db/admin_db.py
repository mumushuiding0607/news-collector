"""
admin_db.py - 后台管理数据库访问层

封装 auth_users、feedback、subscription_records 等表的只读查询操作。
"""
from __future__ import annotations
from script.db import get_conn, put_conn
from script.db.connection import rows_to_dicts as _dict


def list_users(level: str | None = None, phone: str | None = None, page: int = 1, limit: int = 20) -> dict:
    """分页查询用户列表"""
    conn = get_conn()
    try:
        conditions = ["1=1"]
        params = []
        if level:
            conditions.append("subscription_level = ?")
            params.append(level)
        if phone:
            conditions.append("phone LIKE ?")
            params.append(f"%{phone}%")

        offset = (page - 1) * limit
        where = " AND ".join(conditions)

        total = conn.execute(f"SELECT COUNT(*) FROM auth_users WHERE {where}", params).fetchone()[0]
        rows = _dict(conn,
            f"SELECT id, phone, nickname, email, subscription_level, subscription_expire_at, created_at "
            f"FROM auth_users WHERE {where} ORDER BY id DESC LIMIT ? OFFSET ?",
            [*params, limit, offset],
        )
        return {"total": total, "page": page, "limit": limit, "users": rows}
    finally:
        put_conn(conn)


def get_user_detail(user_id: int) -> dict | None:
    """获取用户详情"""
    conn = get_conn()
    try:
        rows = _dict(conn,
            "SELECT id, phone, nickname, email, subscription_level, subscription_expire_at, created_at "
            "FROM auth_users WHERE id = ?",
            (user_id,),
        )
        return rows[0] if rows else None
    finally:
        put_conn(conn)


def update_user_subscription(user_id: int, level: str, days: int, expire_at: str | None) -> dict:
    """变更用户订阅等级"""
    conn = get_conn()
    try:
        conn.execute(
            "UPDATE auth_users SET subscription_level = ?, subscription_expire_at = ?, updated_at = ? WHERE id = ?",
            (level, expire_at, expire_at, user_id),
        )
        conn.commit()
        return {"ok": True, "level": level, "expire_at": expire_at}
    finally:
        put_conn(conn)


def list_feedbacks(page: int = 1, limit: int = 20) -> dict:
    """分页查询反馈列表（关联用户手机号）"""
    conn = get_conn()
    try:
        offset = (page - 1) * limit
        total = conn.execute("SELECT COUNT(*) FROM feedback").fetchone()[0]
        feedback_rows = _dict(conn,
            "SELECT id, user_id, type, content, created_at FROM feedback ORDER BY id DESC LIMIT ? OFFSET ?",
            (limit, offset),
        )
        users_map = {r["id"]: r["phone"] for r in _dict(conn, "SELECT id, phone FROM auth_users")}
        for f in feedback_rows:
            f["phone"] = users_map.get(f["user_id"], "未知")
        return {"total": total, "page": page, "limit": limit, "list": feedback_rows}
    finally:
        put_conn(conn)


def reply_feedback(feedback_id: int, reply: str) -> dict:
    """回复反馈（暂存在 note 字段）"""
    conn = get_conn()
    try:
        conn.execute("UPDATE feedback SET note = ? WHERE id = ?", (reply, feedback_id))
        conn.commit()
        return {"ok": True}
    finally:
        put_conn(conn)


def list_pending_subscriptions() -> list:
    """获取待确认的订阅用户列表"""
    conn = get_conn()
    try:
        return _dict(conn,
            """SELECT sr.id, sr.user_id, sr.level, sr.price, sr.start_at, sr.end_at, sr.status,
                      au.phone, au.email, au.nickname,
                      o.order_no, o.created_at as order_created_at
               FROM subscription_records sr
               JOIN auth_users au ON sr.user_id = au.id
               LEFT JOIN orders o ON o.user_id = sr.user_id AND o.status IN ('paid', 'pending_confirm')
               WHERE sr.status = 'pending_confirm'
               ORDER BY sr.start_at DESC""",
        )
    finally:
        put_conn(conn)


def confirm_subscription(user_id: int) -> dict:
    """确认用户订阅，将 pending_confirm 改为 active"""
    conn = get_conn()
    try:
        conn.execute(
            "UPDATE subscription_records SET status = 'active' "
            "WHERE user_id = ? AND status = 'pending_confirm'",
            (user_id,),
        )
        conn.execute(
            "UPDATE orders SET status = 'paid' WHERE user_id = ? AND status = 'pending_confirm'",
            (user_id,),
        )
        conn.commit()
        return {"ok": True}
    finally:
        put_conn(conn)


def reject_subscription(user_id: int, reason: str = "") -> dict:
    """
    拒绝用户订阅申请：
    1. 将 subscription_records 状态改为 proof_requested
    2. 将 orders 状态改回 pending（让用户可重新上传凭证）
    3. 记录拒绝原因到 note
    """
    conn = get_conn()
    try:
        conn.execute(
            "UPDATE subscription_records SET status = 'proof_requested', note = ? "
            "WHERE user_id = ? AND status = 'pending_confirm'",
            (reason, user_id),
        )
        conn.execute(
            "UPDATE orders SET status = 'pending' "
            "WHERE user_id = ? AND status = 'pending_confirm'",
            (user_id,),
        )
        conn.commit()
        return {"ok": True}
    finally:
        put_conn(conn)


# ============ source_crawl_configs 管理 ============


def list_crawl_configs(checked: int | None = None, page: int = 1, limit: int = 50) -> dict:
    """分页查询 source_crawl_configs"""
    import sqlite3
    from script.bootstrap import get_db_path
    conn = sqlite3.connect(str(get_db_path()))
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conditions = ["1=1"]
        params = []
        if checked is not None:
            conditions.append("checked = ?")
            params.append(checked)

        offset = (page - 1) * limit
        where = " AND ".join(conditions)

        total = conn.execute(f"SELECT COUNT(*) FROM source_crawl_configs WHERE {where}", params).fetchone()[0]
        rows = _dict(conn,
            f"""SELECT id, url_norm, name, source_type, is_flash, checked, list_config, content_extract,
                       publish_time_pattern, crawl_order, created_at, updated_at
                FROM source_crawl_configs WHERE {where}
                ORDER BY checked ASC, id DESC LIMIT ? OFFSET ?""",
            [*params, limit, offset],
        )
        # 解析 list_config JSON
        import json
        for r in rows:
            lc = r.get("list_config", "")
            if lc:
                try:
                    r["list_config_parsed"] = json.loads(lc)
                except Exception:
                    r["list_config_parsed"] = None
            else:
                r["list_config_parsed"] = None

        return {"total": total, "page": page, "limit": limit, "list": rows}
    finally:
        conn.close()


def list_crawl_config_names() -> list[str]:
    """获取所有不重复的数据源名称（只查 name 列，轻量）"""
    import sqlite3
    from script.bootstrap import get_db_path
    conn = sqlite3.connect(str(get_db_path()))
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        rows = conn.execute("SELECT DISTINCT name FROM source_crawl_configs WHERE name IS NOT NULL AND name != '' ORDER BY name").fetchall()
        return [r[0] for r in rows]
    finally:
        conn.close()


def set_crawl_config_checked(config_id: int, checked: int) -> dict:
    """设置 checked 状态"""
    import sqlite3
    from script.bootstrap import get_db_path
    conn = sqlite3.connect(str(get_db_path()))
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute(
            "UPDATE source_crawl_configs SET checked = ?, updated_at = datetime('now','localtime') WHERE id = ?",
            (checked, config_id),
        )
        conn.commit()
        return {"ok": True}
    finally:
        conn.close()


def delete_crawl_configs_record(config_id: int) -> dict:
    """删除 source_crawl_configs 记录"""
    import sqlite3
    from script.bootstrap import get_db_path
    conn = sqlite3.connect(str(get_db_path()))
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("DELETE FROM source_crawl_configs WHERE id = ?", (config_id,))
        conn.commit()
        return {"ok": True}
    finally:
        conn.close()


def delete_crawl_config(config_id: int) -> dict:
    """删除 source_crawl_configs 记录（兼容别名）"""
    return delete_crawl_configs_record(config_id)


def create_crawl_config(name: str, url_norm: str) -> dict:
    """新增数据源配置（插入 url_norm + name，返回新记录）"""
    import sqlite3
    from script.bootstrap import get_db_path
    from script.common.urlutil import normalize_url
    conn = sqlite3.connect(str(get_db_path()))
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        norm = normalize_url(url_norm)
        # 查重
        existing = conn.execute(
            "SELECT id FROM source_crawl_configs WHERE url_norm = ?", (norm,)
        ).fetchone()
        if existing:
            return {"ok": False, "error": "该 URL 已存在"}
        conn.execute(
            "INSERT INTO source_crawl_configs (url_norm, name, checked) VALUES (?, ?, 0)",
            (norm, name),
        )
        conn.commit()
        new_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        return {"ok": True, "id": new_id, "url_norm": norm, "name": name}
    finally:
        conn.close()


def update_crawl_config(config_id: int, name: str | None = None, url_norm: str | None = None,
                        list_config: str | None = None, content_extract: str | None = None,
                        crawl_order: int | None = None, is_flash: int | None = None) -> dict:
    """更新 source_crawl_configs 记录"""
    import sqlite3
    from script.bootstrap import get_db_path
    conn = sqlite3.connect(str(get_db_path()))
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        fields = []
        params = []
        if name is not None:
            fields.append("name = ?")
            params.append(name)
        if url_norm is not None:
            fields.append("url_norm = ?")
            params.append(url_norm)
        if list_config is not None:
            fields.append("list_config = ?")
            params.append(list_config)
        if content_extract is not None:
            fields.append("content_extract = ?")
            params.append(content_extract)
        if crawl_order is not None:
            fields.append("crawl_order = ?")
            params.append(crawl_order)
        if is_flash is not None:
            fields.append("is_flash = ?")
            params.append(is_flash)
        if not fields:
            return {"ok": True}
        fields.append("updated_at = datetime('now','localtime')")
        params.append(config_id)
        conn.execute(
            f"UPDATE source_crawl_configs SET {', '.join(fields)} WHERE id = ?",
            params,
        )
        conn.commit()
        return {"ok": True}
    finally:
        conn.close()


def update_subscription_level(user_id: int, level: str, expire_at: str | None) -> dict:
    """修改用户订阅等级（取消当前生效，插入新记录）"""
    conn = get_conn()
    try:
        now = expire_at
        # 取消当前生效订阅
        conn.execute(
            "UPDATE subscription_records SET status = 'cancelled' "
            "WHERE user_id = ? AND status = 'active'",
            (user_id,),
        )
        # 插入新订阅记录
        cursor = conn.execute(
            "INSERT INTO subscription_records (user_id, level, price, start_at, end_at, status) "
            "VALUES (?, ?, ?, ?, ?, 'active')",
            (user_id, level, 0, now, expire_at),
        )
        # 更新用户订阅状态
        conn.execute(
            "UPDATE auth_users SET subscription_level = ?, subscription_expire_at = ?, updated_at = ? WHERE id = ?",
            (level, expire_at, now, user_id),
        )
        conn.commit()
        return {"ok": True, "level": level, "expire_at": expire_at}
    finally:
        put_conn(conn)