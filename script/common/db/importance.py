"""
db/importance.py - 新闻评分表 CRUD

重要：
  表结构定义在 db/schema.sql 中，不要在此文件中硬编码建表语句。

表结构 (importance):
  id, news_id, batch_id, source_name, title, url, publish_time,
  summary, related_sectors, importance_score, reason,
  direction, intensity, expected_change, duration,
  expectation_level, market_mode, publish_sector_values,
  current_sector_values, created_at

初始化：
  表由 schema.sql 统一创建，如需单独初始化可调用 init_db()。
"""

from .connection import get_conn


# ---------------------------------------------------------------------------
# 写
# ---------------------------------------------------------------------------

def insert(row: dict, commit: bool = True) -> int | None:
    """
    写入一条评分记录到 importance 表。

    row 字段：
        news_id, batch_id, source_name, title, url, publish_time,
        summary, related_sectors, importance_score, reason,
        direction, intensity, expected_change, duration,
        expectation_level, market_mode, publish_sector_values,
        current_sector_values

    返回:
        新记录 id（int），失败返回 None
    """
    conn = get_conn()
    try:
        cur = conn.execute("""
            INSERT INTO importance
                (news_id, batch_id, source_name, title, url, publish_time,
                 summary, related_sectors, importance_score, reason,
                 direction, intensity, expected_change, duration,
                 expectation_level, market_mode, publish_sector_values,
                 current_sector_values, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now','localtime'))
        """, (
            row["news_id"],
            row.get("batch_id", 0),
            row["source_name"],
            row["title"],
            row["url"],
            row["publish_time"],
            row["summary"],
            row["related_sectors"],
            row["importance_score"],
            row["reason"],
            row.get("direction", ""),
            row.get("intensity", 0),
            row.get("expected_change", ""),
            row.get("duration", ""),
            row.get("expectation_level", ""),
            row.get("market_mode", ""),
            row.get("publish_sector_values", ""),
            row.get("current_sector_values", ""),
        ))
        if commit:
            conn.commit()
        return cur.lastrowid
    except Exception:
        return None
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# 读
# ---------------------------------------------------------------------------

def get_recent(limit: int = 20) -> list[tuple]:
    """读取最近评分的新闻（按创建时间倒序）"""
    conn = get_conn()
    cur = conn.execute("""
        SELECT id, news_id, source_name, title, url, publish_time,
               summary, related_sectors, importance_score, reason,
               direction, intensity, expected_change, duration,
               expectation_level, market_mode, publish_sector_values,
               current_sector_values, created_at
        FROM importance
        ORDER BY created_at DESC
        LIMIT ?
    """, (limit,))
    rows = cur.fetchall()
    conn.close()
    return rows


def get_by_score(min_score: int = 7, limit: int = 20) -> list[tuple]:
    """读取评分 >= min_score 的新闻（高重要性）"""
    conn = get_conn()
    cur = conn.execute("""
        SELECT id, news_id, source_name, title, url, publish_time,
               summary, related_sectors, importance_score, reason,
               direction, intensity, expected_change, duration,
               expectation_level, market_mode, publish_sector_values,
               current_sector_values, created_at
        FROM importance
        WHERE importance_score >= ?
        ORDER BY importance_score DESC, created_at DESC
        LIMIT ?
    """, (min_score, limit))
    rows = cur.fetchall()
    conn.close()
    return rows


def get_latest_batch(limit: int = 20) -> list[tuple]:
    """读取最新一批次的新闻（按created_at分组）"""
    conn = get_conn()
    # 获取最新的批次时间
    latest_time = conn.execute("""
        SELECT created_at FROM importance ORDER BY created_at DESC LIMIT 1
    """).fetchone()
    if not latest_time:
        conn.close()
        return []

    cur = conn.execute("""
        SELECT id, news_id, source_name, title, url, publish_time,
               summary, related_sectors, importance_score, reason,
               direction, intensity, expected_change, duration,
               expectation_level, market_mode, publish_sector_values,
               current_sector_values, created_at
        FROM importance
        WHERE created_at = ?
        ORDER BY importance_score DESC
        LIMIT ?
    """, (latest_time[0], limit))
    rows = cur.fetchall()
    conn.close()
    return rows


def get_max_batch_id() -> int | None:
    """获取最新的 batch_id"""
    conn = get_conn()
    try:
        row = conn.execute("SELECT MAX(batch_id) FROM importance").fetchone()
        return row[0] if row and row[0] is not None else None
    finally:
        conn.close()


def get_top_news_by_batch(batch_id: int, top_n: int = 10) -> list[dict]:
    """获取指定批次中得分最高的前 N 条新闻"""
    conn = get_conn()
    try:
        cur = conn.execute("""
            SELECT id, title, related_sectors, publish_time, created_at, importance_score
            FROM importance
            WHERE batch_id = ?
            ORDER BY importance_score DESC
            LIMIT ?
        """, (batch_id, top_n))
        return [
            {
                "id": r[0],
                "title": r[1],
                "related_sectors": r[2],
                "publish_time": r[3],
                "created_at": r[4],
                "importance_score": r[5],
            }
            for r in cur.fetchall()
        ]
    finally:
        conn.close()


def update_publish_sector_values(news_id: int, value_str: str) -> bool:
    """更新单条新闻的 publish_sector_values"""
    conn = get_conn()
    try:
        conn.execute("""
            UPDATE importance
            SET publish_sector_values = ?
            WHERE id = ?
        """, (value_str, news_id))
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()


def batch_update_publish_sector_values(updates: list[tuple[int, str]]) -> int:
    """
    批量更新 publish_sector_values

    Args:
        updates: list of (news_id, value_str)

    Returns:
        更新的记录数
    """
    if not updates:
        return 0
    conn = get_conn()
    try:
        for news_id, value_str in updates:
            conn.execute("""
                UPDATE importance
                SET publish_sector_values = ?
                WHERE id = ?
            """, (value_str, news_id))
        conn.commit()
        return len(updates)
    finally:
        conn.close()