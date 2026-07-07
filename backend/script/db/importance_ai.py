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
    """查询最近 N 条 AI 新闻评分。"""
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM importance_ai ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        cols = [d[0] for d in conn.execute("SELECT * FROM importance_ai LIMIT 0").description]
        return [dict(zip(cols, r)) for r in rows]
    finally:
        put_conn(conn)