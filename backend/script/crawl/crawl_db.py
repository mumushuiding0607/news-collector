"""
crawl_db.py - 爬虫数据库访问层

封装 list_crawler / news_filter / article_crawler 所需的数据库操作。
禁止在这三个模块中直接调用 get_conn()。
"""
from __future__ import annotations
from script.db import get_conn, put_conn
from script.db.primary_source import get_all_urls as _get_all_urls, insert as _db_insert

__all__ = [
    "get_conn", "put_conn",
    "start_batch", "insert_article", "get_all_urls",
    "upsert_list_page", "mark_article_crawled", "delete_article",
    "mark_useful", "get_unfiltered_batch", "get_failed_batch", "get_useful_uncrawled",
]


def start_batch() -> int:
    """为本次采集生成批次号"""
    from script.db.primary_source import get_next_batch_id
    conn = get_conn()
    try:
        return get_next_batch_id(conn=conn)
    finally:
        put_conn(conn)


def insert_article(article: dict, batch_id: int, commit: bool = True) -> bool:
    """插入文章，返回是否成功（自动重试处理 database locked）"""
    import time
    for attempt in range(3):
        conn = get_conn()
        try:
            ok = _db_insert(article, commit=False, conn=conn)
            if commit:
                conn.commit()
            return ok
        except Exception as e:
            if "locked" in str(e) and attempt < 2:
                time.sleep(0.5 * (attempt + 1))
                continue
            raise
        finally:
            put_conn(conn)
    return False


def get_all_urls() -> set:
    """返回所有已入库 URL"""
    return _get_all_urls()


def upsert_list_page(article: dict, batch_id: int) -> bool:
    """列表页直采文章 upsert（自动重试处理 database locked）"""
    import time
    from script.db.primary_source import upsert_list_page_article
    from script.db import get_conn, put_conn
    for attempt in range(3):
        conn = get_conn()
        try:
            ok = upsert_list_page_article(article, commit=False, batch_id=batch_id, conn=conn)
            conn.commit()
            return ok
        except Exception as e:
            if "locked" in str(e) and attempt < 2:
                time.sleep(0.5 * (attempt + 1))
                continue
            raise
        finally:
            put_conn(conn)
    return False


def mark_article_crawled(news_id: int, content: str, content_length: int, publish_time: str) -> None:
    """更新文章正文"""
    from script.db.primary_source import update_content
    update_content(news_id, content, content_length, publish_time)


def delete_article(news_id: int) -> None:
    """删除文章（日期无效等情况下）"""
    from script.db.primary_source import delete_by_id
    delete_by_id(news_id)


def mark_useful(news_id: int, useful: int, commit: bool = True, conn=None) -> None:
    """标记新闻是否有用"""
    from script.db.primary_source import mark_useful as _mark_useful
    _mark_useful(news_id, useful, commit=commit, conn=conn)


def get_unfiltered_batch(conn=None) -> list:
    """获取未过滤批次"""
    from script.db.primary_source import get_unfiltered_batch as _get_batch
    return _get_batch(conn=conn)


def get_failed_batch(conn=None) -> list:
    """获取解析失败的批次"""
    from script.db.primary_source import get_failed_batch as _get_batch
    return _get_batch(conn=conn)


def get_useful_uncrawled() -> list:
    """获取已判定有用且未抓取正文的文章"""
    from script.db.primary_source import get_useful_uncrawled as _get
    return _get()