"""
db/ - 数据库模块

子模块：
  connection  - 连接与初始化（get_conn, init_db）
  primary_source - 一手新闻表 CRUD
  importance    - 评分表 CRUD
  sectors      - 板块数据管理（归一化匹配）

新表：
  importance   - 新闻评分表
  sector_indices - 板块指数记录表
"""

from .connection import get_conn, init_db
from .primary_source import (get_all_urls, get_unread, insert, upsert_list_page_article,
                               mark_scored, mark_read, get_unfiltered_batch, mark_useful, get_useful_uncrawled,
                               get_failed_batch)
from .importance import insert as insert_importance, get_recent, get_by_score as get_recent_by_score, get_latest_batch
from .sectors import normalize, fuzzy_match, search, sync_from_iwencai, count as sectors_count

__all__ = [
    # connection
    "get_conn",
    "init_db",
    # primary_source
    "get_all_urls",
    "get_unread",
    "insert",
    "upsert_list_page_article",
    "mark_scored",
    "mark_read",
    "get_unfiltered_batch",
    "mark_useful",
    "get_useful_uncrawled",
    # importance
    "insert_importance",
    "get_recent",
    "get_recent_by_score",
    # sectors
    "normalize",
    "fuzzy_match",
    "search",
    "sync_from_iwencai",
    "sectors_count",
]