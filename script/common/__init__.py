"""
common/ - 公共模块
"""

from .db.connection import get_conn, init_db
from .db.primary_source import get_all_urls, get_unread, insert, upsert_list_page_article, mark_read
from .db.importance import ensure_table, insert as insert_importance, get_recent, get_by_score as get_recent_by_score, get_latest_batch
from .db.sectors import normalize, fuzzy_match, search, sync_from_iwencai, count as sectors_count

__all__ = [
    "get_conn",
    "init_db",
    "get_all_urls",
    "get_unread",
    "insert",
    "upsert_list_page_article",
    "mark_read",
    "ensure_table",
    "insert_importance",
    "get_recent",
    "get_recent_by_score",
    "get_latest_batch",
    "normalize",
    "fuzzy_match",
    "search",
    "sync_from_iwencai",
    "sectors_count",
]