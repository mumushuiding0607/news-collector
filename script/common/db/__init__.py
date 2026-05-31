"""
db/ - 数据库模块

子模块：
  connection    - 连接与初始化（get_conn, init_db）
  primary_source - 一手新闻表 CRUD
  importance    - 评分表 CRUD
  sectors       - 板块数据管理（归一化匹配）
  rag           - RAG 知识库访问层

重要：
  所有数据库操作必须通过此模块，禁止在其他模块中直接调用 get_conn() 执行 SQL。
"""

from .connection import get_conn, init_db
from .primary_source import (get_all_urls, get_unread, insert, upsert_list_page_article,
                               mark_scored, mark_read, get_unfiltered_batch, mark_useful, get_useful_uncrawled,
                               get_failed_batch)
from .importance import (insert as insert_importance, get_recent, get_by_score as get_recent_by_score,
                         get_latest_batch, get_max_batch_id, get_top_news_by_batch,
                         update_publish_sector_values, batch_update_publish_sector_values)
from .sectors import normalize, fuzzy_match, search, sync_from_iwencai, count as sectors_count
from .rag import (
    upsert_sector, get_sector_by_name, list_sectors,
    insert_stock, insert_eliminated, save_report,
    query_stocks, get_stocks_by_sector, save_all as rag_save_all,
    count_stocks, count_eliminated, delete_sector_stocks
)
from .sector_indices import save_sector_indices, get_sector_indices

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
    "get_latest_batch",
    "get_max_batch_id",
    "get_top_news_by_batch",
    "update_publish_sector_values",
    "batch_update_publish_sector_values",
    # sectors
    "normalize",
    "fuzzy_match",
    "search",
    "sync_from_iwencai",
    "sectors_count",
    # rag
    "upsert_sector",
    "get_sector_by_name",
    "list_sectors",
    "insert_stock",
    "insert_eliminated",
    "save_report",
    "query_stocks",
    "get_stocks_by_sector",
    "rag_save_all",
    "count_stocks",
    "count_eliminated",
    "delete_sector_stocks",
]