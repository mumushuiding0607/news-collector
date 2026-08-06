"""
importance_ai.py - AI 新闻评分表 CRUD

表结构：id, news_id, source_name, title, url, publish_time,
        summary, score, tech_novelty, monetization, domains, highlights, reason, created_at
"""

from .connection import get_conn, put_conn
from script.log import log as _log


def insert_ai(row: dict, conn=None, commit=True) -> bool:
    """
    写入 importance_ai 表。

    - conn=None 时自己获取连接（兼容其他调用方）
    - commit=True 时自动 commit
    - 返回 bool（成功/失败），不再静默抛异常
    """
    local_conn = False
    if conn is None:
        conn = get_conn()
        local_conn = True
    try:
        cur = conn.execute("""
            INSERT OR IGNORE INTO importance_ai
                (news_id, source_name, title, url, publish_time, summary,
                 score, tech_novelty, monetization, domains, highlights, reason, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now','localtime'))
        """, (
            row["news_id"],
            row.get("source_name", ""),
            row.get("title", ""),
            row.get("url", ""),
            row.get("publish_time", ""),
            row.get("summary", ""),
            row.get("score", 0),
            row.get("tech_novelty"),
            row.get("monetization", ""),
            row.get("domains", ""),
            row.get("highlights", ""),
            row.get("reason", ""),
        ))
        if commit:
            conn.commit()
        return cur.rowcount > 0
    except Exception as e:
        _log("importance_ai", f"insert_ai failed: news_id={row.get('news_id')}, e={e}")
        if commit:
            conn.rollback()
        return False
    finally:
        if local_conn:
            put_conn(conn)


def get_recent_ai(limit: int = 50) -> list[dict]:
    """查询最近 N 条 AI 新闻评分（按时间倒序）。"""
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM importance_ai ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        cols = [d[0] for d in conn.execute("SELECT * FROM importance_ai LIMIT 0").description]
        return [dict(zip(cols, r)) for r in rows]
    finally:
        put_conn(conn)


def get_latest_ai(limit: int = 50) -> list[dict]:
    """查询评分最高的 N 条 AI 新闻（按评分倒序）。"""
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM importance_ai ORDER BY score DESC, created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        cols = [d[0] for d in conn.execute("SELECT * FROM importance_ai LIMIT 0").description]
        return [dict(zip(cols, r)) for r in rows]
    finally:
        put_conn(conn)


def get_history_ai(limit: int = 100) -> list[dict]:
    """查询最近 N 条 AI 新闻（按时间倒序）。"""
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM importance_ai ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        cols = [d[0] for d in conn.execute("SELECT * FROM importance_ai LIMIT 0").description]
        return [dict(zip(cols, r)) for r in rows]
    finally:
        put_conn(conn)


def get_latest_ai_with_content(limit: int = 50) -> list[dict]:
    """查询评分最高的 N 条 AI 新闻（含正文内容）。"""
    conn = get_conn()
    try:
        rows = conn.execute("""
            SELECT ia.*, ps.content
            FROM importance_ai ia
            LEFT JOIN primary_sources ps ON ia.news_id = ps.id
            ORDER BY ia.score DESC, ia.created_at DESC
            LIMIT ?
        """, (limit,)).fetchall()
        cols = [d[0] for d in conn.execute("SELECT * FROM importance_ai LIMIT 0").description] + ["content"]
        return [dict(zip(cols, r)) for r in rows]
    finally:
        put_conn(conn)


def get_history_ai_with_content(limit: int = 100) -> list[dict]:
    """查询最近 N 条 AI 新闻（含正文内容）。"""
    conn = get_conn()
    try:
        rows = conn.execute("""
            SELECT ia.*, ps.content
            FROM importance_ai ia
            LEFT JOIN primary_sources ps ON ia.news_id = ps.id
            ORDER BY ia.created_at DESC
            LIMIT ?
        """, (limit,)).fetchall()
        cols = [d[0] for d in conn.execute("SELECT * FROM importance_ai LIMIT 0").description] + ["content"]
        return [dict(zip(cols, r)) for r in rows]
    finally:
        put_conn(conn)


def query_news_ai_admin(
    where_clause: str, params: tuple, page: int, limit: int
) -> tuple[list[dict], int]:
    """
    AI 新闻管理分页查询（直接查 importance_ai 表）。

    Returns:
        (items: list[dict], total: int)
    """
    conn = get_conn()
    try:
        count_sql = f"SELECT COUNT(*) FROM importance_ai ia WHERE {where_clause}"
        total = conn.execute(count_sql, params).fetchone()[0]

        offset = (page - 1) * limit
        data_sql = f"""
            SELECT ia.*
            FROM importance_ai ia
            WHERE {where_clause}
            ORDER BY ia.id DESC
            LIMIT ? OFFSET ?
        """
        cur = conn.execute(data_sql, (*params, limit, offset))
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description]
        items = [dict(zip(cols, r)) for r in rows]
        return items, total
    finally:
        put_conn(conn)