"""
anomaly_news.py - 异动消息表 CRUD
"""
from .connection import get_conn, put_conn
from script.common.datetimeutil import now_iso


def save_anomaly_news(title: str, url: str, publish_time: str, source_name: str, processed: int = 0, content: str = "") -> int:
    """
    保存单条异动消息到数据库。

    Returns:
        int: 新插入记录的 id，失败返回 0
    """
    conn = get_conn()
    try:
        created_at = now_iso()
        content_length = len(content) if content else 0
        cursor = conn.execute(
            """INSERT INTO anomaly_news (title, url, publish_time, source_name, processed, content, content_length, content_crawled_at, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, NULL, ?)""",
            (title, url, publish_time, source_name, processed, content, content_length, created_at),
        )
        conn.commit()
        return cursor.lastrowid if cursor.lastrowid else 0
    except Exception:
        return 0
    finally:
        put_conn(conn)


def batch_save_anomaly_news(anomalies: list[dict]) -> int:
    """
    批量保存异动消息（根据 URL 去重）

    Args:
        anomalies: [{title, url, publish_time, source_name}, ...]

    Returns:
        int: 成功保存的数量
    """
    conn = get_conn()
    count = 0
    created_at = now_iso()

    # 查询已有 URL
    existing = {row[0] for row in conn.execute("SELECT url FROM anomaly_news")}
    seen: set[str] = set()

    try:
        for a in anomalies:
            url = a.get('url', '')
            if not url or url in seen or url in existing:
                continue
            seen.add(url)

            source_name = a.get('source_name', '')

            content = a.get('content', '')
            cursor = conn.execute(
                """INSERT INTO anomaly_news (title, url, publish_time, source_name, processed, content, content_length, content_crawled_at, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, NULL, ?)""",
                (
                    a.get('title', ''),
                    url,
                    a.get('publish_time', ''),
                    source_name,
                    0,
                    content,
                    len(content) if content else 0,
                    created_at,
                ),
            )
            if cursor.lastrowid:
                count += 1
        conn.commit()
    finally:
        put_conn(conn)
    return count


def get_anomaly_news(
    source_name: str = None,
    title: str = None,
    limit: int = 100,
    offset: int = 0,
    processed: int | None = None,
) -> list:
    """获取异动消息（支持分页和已处理状态过滤）"""
    conn = get_conn()
    try:
        where_clauses: list[str] = []
        params: list = []
        if source_name:
            where_clauses.append("source_name = ?")
            params.append(source_name)
        if title:
            where_clauses.append("title LIKE ?")
            params.append(f"%{title}%")
        if processed is not None:
            where_clauses.append("processed = ?")
            params.append(processed)
        where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
        sql = f"""SELECT id, title, url, publish_time, source_name, processed, created_at
                  FROM anomaly_news {where_sql}
                  ORDER BY publish_time DESC LIMIT ? OFFSET ?"""
        cur = conn.execute(sql, (*params, limit, offset))
        return cur.fetchall()
    finally:
        put_conn(conn)


def count_anomaly_news(source_name: str = None, title: str = None, processed: int | None = None) -> int:
    """统计异动消息数量（用于分页总数）"""
    conn = get_conn()
    try:
        where_clauses: list[str] = []
        params: list = []
        if source_name:
            where_clauses.append("source_name = ?")
            params.append(source_name)
        if title:
            where_clauses.append("title LIKE ?")
            params.append(f"%{title}%")
        if processed is not None:
            where_clauses.append("processed = ?")
            params.append(processed)
        where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
        sql = f"SELECT COUNT(*) FROM anomaly_news {where_sql}"
        cur = conn.execute(sql, params)
        return int(cur.fetchone()[0])
    finally:
        put_conn(conn)


def mark_processed(id: int) -> bool:
    """标记为已处理"""
    conn = get_conn()
    try:
        conn.execute("UPDATE anomaly_news SET processed = 1 WHERE id = ?", (id,))
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        put_conn(conn)


def mark_all_processed() -> int:
    """标记所有为已处理"""
    conn = get_conn()
    try:
        conn.execute("UPDATE anomaly_news SET processed = 1 WHERE processed = 0")
        conn.commit()
        return conn.total_changes
    except Exception:
        return 0
    finally:
        put_conn(conn)


def toggle_processed(id: int) -> tuple[bool, int]:
    """切换处理状态，返回 (是否成功, 切换后的状态)"""
    conn = get_conn()
    try:
        # 获取当前状态
        cur = conn.execute("SELECT processed FROM anomaly_news WHERE id = ?", (id,))
        row = cur.fetchone()
        if not row:
            return False, -1
        new_state = 0 if row[0] else 1
        conn.execute("UPDATE anomaly_news SET processed = ? WHERE id = ?", (new_state, id))
        conn.commit()
        return True, new_state
    except Exception:
        return False, -1
    finally:
        put_conn(conn)


def get_anomaly_news_by_date(date_str: str, limit: int = 200) -> list:
    """获取指定日期的异动消息"""
    conn = get_conn()
    try:
        cur = conn.execute(
            """SELECT id, title, url, publish_time, source_name, processed, created_at
               FROM anomaly_news WHERE date(publish_time) = date(?) ORDER BY created_at DESC LIMIT ?""",
            (date_str, limit),
        )
        return cur.fetchall()
    finally:
        put_conn(conn)


def get_anomaly_news_by_date_with_content(date_str: str, limit: int = 200) -> list:
    """获取指定日期的异动消息（包含正文，用于简报生成）"""
    conn = get_conn()
    try:
        cur = conn.execute(
            """SELECT id, title, url, publish_time, source_name, content, processed, created_at
               FROM anomaly_news WHERE date(publish_time) = date(?) ORDER BY created_at DESC LIMIT ?""",
            (date_str, limit),
        )
        return cur.fetchall()
    finally:
        put_conn(conn)


def get_latest_anomaly_date() -> str | None:
    """获取异动消息表中最新日期"""
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT date(max(publish_time)) as latest_date FROM anomaly_news"
        ).fetchone()
        return row[0] if row else None
    finally:
        put_conn(conn)


def get_anomaly_news_by_source_latest_date(source_name: str, limit: int = 100) -> list:
    """获取指定数据源最新日期的异动消息"""
    conn = get_conn()
    try:
        # 先获取该数据源的最新日期
        row = conn.execute(
            "SELECT date(max(publish_time)) FROM anomaly_news WHERE source_name = ?",
            (source_name,),
        ).fetchone()
        if not row or not row[0]:
            return []
        latest_date = row[0]
        # 再获取该日期的异动消息
        cur = conn.execute(
            """SELECT id, title, url, publish_time, source_name, processed, created_at
               FROM anomaly_news
               WHERE source_name = ? AND date(publish_time) = date(?)
               ORDER BY publish_time DESC LIMIT ?""",
            (source_name, latest_date, limit),
        )
        return cur.fetchall()
    finally:
        put_conn(conn)


def delete_anomaly_news(id: int) -> bool:
    """删除异动消息"""
    conn = get_conn()
    try:
        conn.execute("DELETE FROM anomaly_news WHERE id = ?", (id,))
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        put_conn(conn)


def update_anomaly_content(news_id: int, content: str, source_name: str = "") -> bool:
    """更新异动消息的正文内容和/或数据源名称"""
    conn = get_conn()
    try:
        content_length = len(content) if content else 0
        if source_name:
            conn.execute(
                "UPDATE anomaly_news SET content = ?, content_length = ?, content_crawled_at = ?, source_name = ? WHERE id = ?",
                (content, content_length, now_iso(), source_name, news_id),
            )
        else:
            conn.execute(
                "UPDATE anomaly_news SET content = ?, content_length = ?, content_crawled_at = ? WHERE id = ?",
                (content, content_length, now_iso(), news_id),
            )
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        put_conn(conn)


def get_anomaly_news_for_content_crawl(limit: int = 200) -> list:
    """获取待采集正文的异动消息（content 为空且有 url）"""
    conn = get_conn()
    try:
        cur = conn.execute(
            """SELECT id, title, url, publish_time, source_name
               FROM anomaly_news
               WHERE url IS NOT NULL AND url != '' AND (content IS NULL OR content = '')
               ORDER BY created_at ASC LIMIT ?""",
            (limit,),
        )
        return cur.fetchall()
    finally:
        put_conn(conn)