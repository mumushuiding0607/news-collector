"""
importance_ai.py - AI 新闻评分表 CRUD

表结构：id, news_id, source_name, title, url, publish_time,
        summary, score, tech_novelty, monetization, domains, highlights, reason, created_at
"""

from .connection import get_conn, put_conn

def insert_ai(row: dict, commit: bool = True) -> int | None:
    """写入 importance_ai 表。返回新记录 id，失败返回 None。"""
    conn = get_conn()
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
        return cur.lastrowid
    except Exception:
        return None
    finally:
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


def _row_to_ai_with_content(row, cols) -> dict:
    """将 importance_ai 行转为 dict，并附加 primary_sources.content"""
    d = dict(zip(cols, row))
    return d


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