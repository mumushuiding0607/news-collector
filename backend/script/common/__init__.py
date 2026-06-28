"""
common/ - 新闻采集系统公共模块（向后兼容）

重要：
  此模块已迁移到新结构：
    - 数据库操作 → script/db/
    - 日志 → script/log/
    - 配置 → script/config/

  新代码请使用：
    from script.db import get_conn, init_db
    from script.log import log
    from script.config import LLM_API_KEY

  此模块提供向后兼容导出。
"""

# ==================== 数据库（从 script/db/ 导出）====================

from script.db import (
    get_conn, init_db,
    get_all_urls, get_unread, insert, upsert_list_page_article,
    mark_scored, mark_read, get_unfiltered_batch, mark_useful, get_useful_uncrawled,
    get_failed_batch, delete_by_id, update_content, batch_insert,
    insert as insert_importance,
    get_recent, get_recent_by_score,
    get_latest_batch, get_max_batch_id, get_top_news_by_batch,
    update_publish_sector_values, batch_update_publish_sector_values,
    normalize, fuzzy_match, search, sync_from_iwencai, sectors_count,
    upsert_sector,
    save_sector_indices, get_sector_indices,
)


# ==================== 日志（从 script/log/ 导出）====================

from script.log import log, timestamp_print


# ==================== 配置（从 script/config/ 导出）====================

from script.config import (
    APP_ROOT, DB_PATH, LOG_DIR, CACHE_DIR, CONFIG_DIR, PROMPT_DIR, SOURCES_CONFIG,
    LLM_API_KEY, LLM_BASE_URL, LLM_MODEL,
)


# ==================== 兼容性别名 ====================

__all__ = [
    # 数据库
    "get_conn", "init_db",
    "get_all_urls", "get_unread", "insert", "upsert_list_page_article",
    "mark_scored", "mark_read", "get_unfiltered_batch", "mark_useful", "get_useful_uncrawled",
    "get_failed_batch", "delete_by_id", "update_content", "batch_insert",
    "insert_importance",
    "get_recent", "get_recent_by_score", "get_latest_batch", "get_max_batch_id", "get_top_news_by_batch",
    "update_publish_sector_values", "batch_update_publish_sector_values",
    "normalize", "fuzzy_match", "search", "sync_from_iwencai", "sectors_count",
    "upsert_sector",
    "save_sector_indices", "get_sector_indices",
    # 日志
    "log", "timestamp_print",
    # 配置
    "APP_ROOT", "DB_PATH", "LOG_DIR", "CACHE_DIR", "CONFIG_DIR", "PROMPT_DIR", "SOURCES_CONFIG",
    "LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL",
]