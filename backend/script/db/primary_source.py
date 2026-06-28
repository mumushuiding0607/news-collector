"""
db/primary_source.py - 一手新闻表 CRUD

表结构 (primary_sources):
  id, source_name, title, url UNIQUE, summary, publish_time,
  content, content_length, status, fetched_at
"""

from .connection import get_conn, put_conn


# ---------------------------------------------------------------------------
# 读
# ---------------------------------------------------------------------------

def get_all_urls() -> set[str]:
    """返回数据库中所有已入库的 URL（用于去重）"""
    conn = get_conn()
    cur = conn.execute("SELECT url FROM primary_sources WHERE url IS NOT NULL AND url != ''")
    urls = {row[0] for row in cur.fetchall()}
    put_conn(conn)
    return urls


def get_by_id(news_id: int) -> dict | None:
    """根据 ID 获取原始新闻详情"""
    conn = get_conn()
    try:
        row = conn.execute("""
            SELECT id, source_name, title, url, summary, publish_time,
                   content, content_length, status, fetched_at
            FROM primary_sources WHERE id = ?
        """, (news_id,)).fetchone()
        if not row:
            return None
        return {
            "id": row[0],
            "source_name": row[1],
            "title": row[2],
            "url": row[3],
            "summary": row[4],
            "publish_time": row[5],
            "content": row[6],
            "content_length": row[7],
            "status": row[8],
            "fetched_at": row[9],
        }
    finally:
        put_conn(conn)


def get_unread(limit: int = 10) -> list[tuple]:
    """读取最新批次中 status='read' 且 is_useful=1 待评分的新闻，按发布时间倒序。

    SQL 层过滤掉 publish_time 为空的记录（这类新闻 scorer 必然跳过，
    提前过滤避免无谓 IO 与日志噪声；具体日期是否当天的判断仍在 Python 层）。
    """
    conn = get_conn()
    cur = conn.execute("""
        SELECT id, source_name, title, url, summary, publish_time, content, batch_id
        FROM primary_sources
        WHERE status = 'read'
          AND is_useful = 1
          AND batch_id = (SELECT MAX(batch_id) FROM primary_sources)
          AND publish_time IS NOT NULL
          AND publish_time != ''
        ORDER BY publish_time DESC
        LIMIT ?
    """, (limit,))
    rows = cur.fetchall()
    put_conn(conn)
    return rows


# ---------------------------------------------------------------------------
# 写
# ---------------------------------------------------------------------------

def get_next_batch_id(conn=None) -> int:
    """获取下一个批次号（当前最大+1）"""
    must_close = conn is None
    if conn is None:
        conn = get_conn()
    try:
        cur = conn.execute("SELECT COALESCE(MAX(batch_id), 0) + 1 FROM primary_sources")
        return cur.fetchone()[0]
    finally:
        if must_close:
            put_conn(conn)


def insert(article: dict, commit: bool = True, conn=None) -> bool:
    """
    写入一条一手新闻到 primary_sources。

    article 字段：
        source_name, title, url, summary, publish_time,
        content, content_length（可选）, batch_id（可选）

    conn: 可选，传入已有连接以支持事务统一提交。

    返回:
        True  = 新增成功
        False = 已存在（INSERT OR IGNORE）
    """
    must_close = conn is None
    if conn is None:
        conn = get_conn()
    try:
        batch_id = article.get("batch_id")
        if batch_id is None:
            batch_id = get_next_batch_id(conn)
        conn.execute("""
            INSERT OR IGNORE INTO primary_sources
                (source_name, title, url, summary, publish_time,
                 content, content_length, batch_id, status, fetched_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'new', datetime('now','localtime'))
        """, (
            article.get("source_name", ""),
            article.get("title", ""),
            article.get("url", ""),
            article.get("summary", ""),
            article.get("publish_time", ""),
            article.get("content", ""),
            article.get("content_length", 0),
            batch_id,
        ))
        if commit:
            conn.commit()
        return conn.total_changes > 0
    finally:
        if must_close:
            put_conn(conn)


def upsert_list_page_article(article: dict, commit: bool = True, batch_id: int = None, conn=None) -> bool:
    """列表页直采模式写入（content 可能是摘要，url 可能为空）"""
    must_close = conn is None
    if conn is None:
        conn = get_conn()
    try:
        if batch_id is None:
            batch_id = get_next_batch_id(conn)

        content = article.get("content", "") or ""
        publish_time = article.get("publish_time", "") or ""

        conn.execute("""
            INSERT OR IGNORE INTO primary_sources
                (source_name, title, url, summary, publish_time,
                 content, content_length, batch_id, status, fetched_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'new', datetime('now','localtime'))
        """, (
            article.get("source_name", ""),
            article.get("title", ""),
            article.get("url", ""),
            article.get("summary", ""),
            publish_time,
            content,
            len(content),
            batch_id,
        ))
        if commit:
            conn.commit()
        return conn.total_changes > 0
    finally:
        if must_close:
            put_conn(conn)


# ---------------------------------------------------------------------------
# 更新
# ---------------------------------------------------------------------------

def mark_scored(news_id: int, commit: bool = True):
    """标记新闻为已评分"""
    conn = get_conn()
    try:
        conn.execute(
            "UPDATE primary_sources SET status='scored' WHERE id=?",
            (news_id,)
        )
        if commit:
            conn.commit()
    finally:
        put_conn(conn)


def mark_read(news_id: int, commit: bool = True):
    """标记新闻为已读（兼容旧代码）"""
    conn = get_conn()
    try:
        conn.execute(
            "UPDATE primary_sources SET status='read' WHERE id=?",
            (news_id,)
        )
        if commit:
            conn.commit()
    finally:
        put_conn(conn)


# ---------------------------------------------------------------------------
# Step 2 辅助
# ---------------------------------------------------------------------------

def get_unfiltered_batch(conn=None) -> list[tuple]:
    """
    读取最新批次（batch_id=MAX）且 is_useful=0 的新闻，
    按发布时间倒序。
    """
    must_close = conn is None
    if conn is None:
        conn = get_conn()
    try:
        cur = conn.execute("""
            SELECT id, source_name, title, url, summary, publish_time, content
            FROM primary_sources
            WHERE is_useful = 0
              AND batch_id = (SELECT MAX(batch_id) FROM primary_sources)
            ORDER BY publish_time DESC
        """)
        rows = cur.fetchall()
        return rows
    finally:
        if must_close:
            put_conn(conn)


def mark_useful(news_id: int, useful: int, commit: bool = True, conn=None):
    """
    标记新闻是否有用。

    useful: 1=有用, -1=无用, 0=未评估
    """
    must_close = conn is None
    if conn is None:
        conn = get_conn()
    try:
        conn.execute(
            "UPDATE primary_sources SET is_useful=? WHERE id=?",
            (useful, news_id)
        )
        if commit:
            conn.commit()
    finally:
        if must_close:
            put_conn(conn)


def get_failed_batch(conn=None) -> list[tuple]:
    """
    读取最新批次（batch_id=MAX）且 is_useful=-1 的新闻（解析失败待重试），
    按发布时间倒序。
    """
    must_close = conn is None
    if conn is None:
        conn = get_conn()
    try:
        cur = conn.execute("""
            SELECT id, source_name, title, url, summary, publish_time, content
            FROM primary_sources
            WHERE is_useful = -1
              AND batch_id = (SELECT MAX(batch_id) FROM primary_sources)
            ORDER BY publish_time DESC
        """)
        rows = cur.fetchall()
        return rows
    finally:
        if must_close:
            put_conn(conn)


def get_useful_uncrawled(conn=None) -> list[tuple]:
    """
    读取最新批次中 is_useful=1 且 status='new' 的记录（Step 3 用）。
    """
    must_close = conn is None
    if conn is None:
        conn = get_conn()
    try:
        cur = conn.execute("""
            SELECT id, source_name, title, url, summary, publish_time
            FROM primary_sources
            WHERE is_useful = 1
              AND status = 'new'
              AND batch_id = (SELECT MAX(batch_id) FROM primary_sources)
            ORDER BY publish_time DESC
        """)
        return cur.fetchall()
    finally:
        if must_close:
            put_conn(conn)


def delete_by_id(news_id: int, commit: bool = True, conn=None) -> bool:
    """根据ID删除记录"""
    must_close = conn is None
    if conn is None:
        conn = get_conn()
    try:
        conn.execute("DELETE FROM primary_sources WHERE id=?", (news_id,))
        if commit:
            conn.commit()
        return True
    finally:
        if must_close:
            put_conn(conn)


def delete_by_fetched_date(date_str: str, commit: bool = True, conn=None) -> int:
    """
    根据抓取日期（fetched_at）删除记录，返回删除数量。
    date_str 格式：YYYY-MM-DD
    使用范围查询以便利用索引。
    """
    from datetime import datetime, timedelta
    next_day = (datetime.strptime(date_str, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
    must_close = conn is None
    if conn is None:
        conn = get_conn()
    try:
        cursor = conn.execute(
            "DELETE FROM primary_sources WHERE fetched_at >= ? AND fetched_at < ?",
            (date_str + " 00:00:00", next_day + " 00:00:00")
        )
        if commit:
            conn.commit()
        return cursor.rowcount
    finally:
        if must_close:
            put_conn(conn)


def update_content(news_id: int, content: str, content_length: int, publish_time: str, commit: bool = True, conn=None) -> bool:
    """更新文章正文内容"""
    must_close = conn is None
    if conn is None:
        conn = get_conn()
    try:
        conn.execute("""
            UPDATE primary_sources
            SET content=?, content_length=?, publish_time=?, status='read'
            WHERE id=?
        """, (content, content_length, publish_time, news_id))
        if commit:
            conn.commit()
        return True
    finally:
        if must_close:
            put_conn(conn)


def batch_insert(articles: list[dict], batch_id: int, conn=None) -> int:
    """
    批量插入文章（使用共享连接以提高性能）

    Args:
        articles: 文章列表，每个 dict 包含 source_name, title, url, summary, publish_time, content
        batch_id: 批次号
        conn: 可选共享连接

    Returns:
        插入成功的数量
    """
    must_close = conn is None
    if conn is None:
        conn = get_conn()
    try:
        count = 0
        for article in articles:
            conn.execute("""
                INSERT OR IGNORE INTO primary_sources
                    (source_name, title, url, summary, publish_time,
                     content, content_length, batch_id, status, fetched_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'new', datetime('now','localtime'))
            """, (
                article.get("source_name", ""),
                article.get("title", ""),
                article.get("url", ""),
                article.get("summary", ""),
                article.get("publish_time", ""),
                article.get("content", ""),
                len(article.get("content", "") or ""),
                batch_id,
            ))
            if conn.total_changes > 0:
                count += 1
        conn.commit()
        return count
    finally:
        if must_close:
            put_conn(conn)