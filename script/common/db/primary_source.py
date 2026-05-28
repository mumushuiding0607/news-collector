"""
db/primary_source.py - 一手新闻表 CRUD

表结构 (primary_sources):
  id, source_name, title, url UNIQUE, subtitle, publish_time,
  content, content_length, status, fetched_at, content_fetched_at
"""

from .connection import get_conn


# ---------------------------------------------------------------------------
# 读
# ---------------------------------------------------------------------------

def get_all_urls() -> set[str]:
    """返回数据库中所有已入库的 URL（用于去重）"""
    conn = get_conn()
    cur = conn.execute("SELECT url FROM primary_sources")
    urls = {row[0] for row in cur.fetchall()}
    conn.close()
    return urls


def get_unread(limit: int = 10) -> list[tuple]:
    """读取待评分的新闻（status='new'），按发布时间倒序"""
    conn = get_conn()
    cur = conn.execute("""
        SELECT id, source_name, title, url, subtitle, publish_time, content
        FROM primary_sources
        WHERE status = 'new'
        ORDER BY publish_time DESC
        LIMIT ?
    """, (limit,))
    rows = cur.fetchall()
    conn.close()
    return rows


# ---------------------------------------------------------------------------
# 写
# ---------------------------------------------------------------------------

def insert(article: dict, commit: bool = True) -> bool:
    """
    写入一条一手新闻到 primary_sources。

    article 字段：
        source_name, title, url, subtitle, publish_time,
        content, content_length（可选）

    返回:
        True  = 新增成功
        False = 已存在（INSERT OR IGNORE）
    """
    conn = get_conn()
    try:
        conn.execute("""
            INSERT OR IGNORE INTO primary_sources
                (source_name, title, url, subtitle, publish_time,
                 content, content_length, status, fetched_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'new', datetime('now','localtime'))
        """, (
            article.get("source_name", ""),
            article.get("title", ""),
            article.get("url", ""),
            article.get("subtitle", ""),
            article.get("publish_time", ""),
            article.get("content", ""),
            article.get("content_length", 0),
        ))
        if commit:
            conn.commit()
        return conn.total_changes > 0
    finally:
        conn.close()


def upsert_list_page_article(article: dict, commit: bool = True) -> bool:
    """列表页直采模式写入（content 可能是摘要，url 可能为空）"""
    conn = get_conn()
    try:
        conn.execute("""
            INSERT OR IGNORE INTO primary_sources
                (source_name, title, url, subtitle, publish_time,
                 content, content_length, status, fetched_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'new', datetime('now','localtime'))
        """, (
            article.get("source_name", ""),
            article.get("title", ""),
            article.get("url", ""),
            article.get("subtitle", ""),
            article.get("publish_time", ""),
            article.get("content", ""),
            len(article.get("content", "") or ""),
        ))
        if commit:
            conn.commit()
        return conn.total_changes > 0
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# 更新
# ---------------------------------------------------------------------------

def mark_read(news_id: int, commit: bool = True):
    """标记新闻为已读"""
    conn = get_conn()
    try:
        conn.execute(
            "UPDATE primary_sources SET status='read' WHERE id=?",
            (news_id,)
        )
        if commit:
            conn.commit()
    finally:
        conn.close()