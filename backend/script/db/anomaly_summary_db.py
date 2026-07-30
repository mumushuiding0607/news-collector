"""
anomaly_summary_db.py - 简报数据库操作
"""
import json
from typing import Any

from script.db.connection import get_conn, put_conn


def save_summary(
    date_str: str,
    content: dict[str, Any],
    summary_type: str = "异动简报",
) -> dict:
    """保存简报，如果日期+类型已存在则更新"""
    conn = get_conn()
    cursor = conn.cursor()

    content_json = json.dumps(content, ensure_ascii=False)

    cursor.execute(
        """
        INSERT INTO summary (date, type, content, created_at)
        VALUES (?, ?, ?, datetime('now','localtime'))
        ON CONFLICT(date, type) DO UPDATE SET
          content = excluded.content,
          created_at = datetime('now','localtime')
        """,
        (date_str, summary_type, content_json),
    )
    conn.commit()
    put_conn(conn)

    return {"success": True, "date": date_str, "type": summary_type}


def get_summary(date_str: str) -> dict | None:
    """获取指定日期的简报"""
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT date, type, content, created_at FROM summary WHERE date = ?",
        (date_str,),
    )
    row = cursor.fetchone()
    put_conn(conn)

    if not row:
        return None

    try:
        content = json.loads(row[2])
    except (json.JSONDecodeError, TypeError):
        content = row[2]

    return {
        "date": row[0],
        "type": row[1],
        "content": content,
        "created_at": row[3],
    }


def get_latest_summary() -> dict | None:
    """获取最新的一条简报（按 date + created_at 倒序）"""
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT date, type, content, created_at FROM summary
        ORDER BY date DESC, created_at DESC
        LIMIT 1
        """,
    )
    row = cursor.fetchone()
    put_conn(conn)

    if not row:
        return None

    try:
        content = json.loads(row[2])
    except (json.JSONDecodeError, TypeError):
        content = row[2]

    return {
        "date": row[0],
        "type": row[1],
        "content": content,
        "created_at": row[3],
    }


def get_summary_by_date_and_type(date_str: str, summary_type: str) -> dict | None:
    """获取指定日期和类型的简报"""
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT date, type, content, created_at FROM summary WHERE date = ? AND type = ?",
        (date_str, summary_type),
    )
    row = cursor.fetchone()
    put_conn(conn)

    if not row:
        return None

    try:
        content = json.loads(row[2])
    except (json.JSONDecodeError, TypeError):
        content = row[2]

    return {
        "date": row[0],
        "type": row[1],
        "content": content,
        "created_at": row[3],
    }


def list_summaries_full(page: int = 1, limit: int = 20) -> dict:
    """
    分页查询简报列表（包含完整 content 内容）。
    用于缓存为空时从数据库重建缓存。
    """
    conn = get_conn()
    cursor = conn.cursor()

    offset = (page - 1) * limit

    cursor.execute("SELECT COUNT(*) FROM summary")
    total = cursor.fetchone()[0]

    cursor.execute(
        """
        SELECT date, type, content, created_at FROM summary
        ORDER BY date DESC, created_at DESC
        LIMIT ? OFFSET ?
        """,
        (limit, offset),
    )
    rows = cursor.fetchall()
    put_conn(conn)

    items = []
    for r in rows:
        try:
            content = json.loads(r[2])
        except (json.JSONDecodeError, TypeError):
            content = r[2]
        items.append({
            "date": r[0],
            "type": r[1],
            "content": content,
            "created_at": r[3],
        })

    return {"total": total, "page": page, "limit": limit, "items": items}


def list_summaries(page: int = 1, limit: int = 20, summary_type: str | None = None) -> dict:
    """分页查询简报列表"""
    conn = get_conn()
    cursor = conn.cursor()

    offset = (page - 1) * limit

    where_clause = "WHERE type = ?" if summary_type else ""
    count_sql = f"SELECT COUNT(*) FROM summary {where_clause}"
    cursor.execute(count_sql, (summary_type,) if summary_type else ())
    total = cursor.fetchone()[0]

    select_sql = f"""
        SELECT date, type, created_at FROM summary
        {where_clause}
        ORDER BY date DESC
        LIMIT ? OFFSET ?
    """
    cursor.execute(select_sql, ((summary_type, limit, offset) if summary_type else (limit, offset)))
    rows = cursor.fetchall()
    put_conn(conn)

    items = [
        {"date": r[0], "type": r[1], "created_at": r[2]}
        for r in rows
    ]

    return {"total": total, "page": page, "limit": limit, "items": items}


def list_summaries_by_date(page: int = 1, limit: int = 20, summary_type: str | None = None) -> dict:
    """
    按最新日期查询简报列表，每个日期只保留最新的一条简报（按 created_at 倒序）。
    用于侧边栏简报入口展示。
    """
    conn = get_conn()
    cursor = conn.cursor()

    where_clause = "WHERE type = ?" if summary_type else ""
    # 子查询：每个日期取最新的一条
    cursor.execute(
        f"""
        SELECT COUNT(*) FROM (
            SELECT date, type, MAX(created_at) as latest_at
            FROM summary
            {where_clause}
            GROUP BY date, type
        )
        """,
        ((summary_type,) if summary_type else ()),
    )
    total = cursor.fetchone()[0]

    offset = (page - 1) * limit
    cursor.execute(
        f"""
        SELECT s.date, s.type, s.created_at
        FROM summary s
        INNER JOIN (
            SELECT date, type, MAX(created_at) as latest_at
            FROM summary
            {where_clause}
            GROUP BY date, type
        ) t ON s.date = t.date AND s.type = t.type AND s.created_at = t.latest_at
        ORDER BY s.date DESC, s.created_at DESC
        LIMIT ? OFFSET ?
        """,
        ((summary_type, limit, offset) if summary_type else (limit, offset)),
    )
    rows = cursor.fetchall()
    put_conn(conn)

    items = [
        {"date": r[0], "type": r[1], "created_at": r[2]}
        for r in rows
    ]

    return {"total": total, "page": page, "limit": limit, "items": items}


def delete_summary_before_date(date_str: str) -> int:
    """删除指定日期之前的所有简报，返回删除数量"""
    conn = get_conn()
    try:
        cursor = conn.execute("DELETE FROM summary WHERE date < ?", (date_str,))
        conn.commit()
        return cursor.rowcount
    finally:
        put_conn(conn)