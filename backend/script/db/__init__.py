"""
db/ - 数据库模块

子模块：
  connection    - 连接与初始化（get_conn, init_db）
  primary_source - 一手新闻表 CRUD
  importance    - 评分表 CRUD
  sectors       - 板块数据管理（归一化匹配）
重要：
  所有数据库操作必须通过此模块，禁止在其他模块中直接调用 get_conn() 执行 SQL。
"""

from .connection import get_conn, put_conn, init_db
from .primary_source import (get_all_urls, get_unread, insert, upsert_list_page_article,
                               mark_scored, mark_read, get_unfiltered_batch, mark_useful, get_useful_uncrawled,
                               get_failed_batch, delete_by_id, update_content, batch_insert)
from .importance import (insert as insert_importance, get_recent, get_by_score as get_recent_by_score,
                         get_latest_batch, get_max_batch_id, get_top_news_by_batch,
                         update_publish_sector_values, batch_update_publish_sector_values,
                         get_positive_by_date, get_latest_importance_date)
from .sectors import normalize, fuzzy_match, search, sync_from_iwencai, count as sectors_count, list_all
from .sectors_crud import upsert_sector
from .sector_indices import save_sector_indices, get_sector_indices
from .auth_db import (
    upsert_phone_code, get_valid_phone_code, mark_phone_code_used,
    upsert_email_code, get_valid_email_code, mark_email_code_used, check_email_exists,
    upsert_reset_code, get_valid_reset_code, mark_reset_code_used,
    phone_exists, get_user_by_phone, get_user_by_email,
    create_user, update_user_password_by_email,
    create_token, get_user_by_token, delete_token,
    is_login_locked, record_login_attempt, lock_phone,
    create_order, get_order, update_order_paid, get_orders_by_user,
)
from .admin_db import (
    list_users, get_user_detail, update_user_subscription,
    list_feedbacks, reply_feedback,
    list_pending_subscriptions, confirm_subscription, update_subscription_level,
    reject_subscription,
    list_crawl_configs, set_crawl_config_checked, delete_crawl_config,
)
from .news_db import query_news, get_news_by_id, query_news_admin, query_primary_sources_admin, get_news_source_name
from .importance_ai import insert_ai, get_recent_ai, get_latest_ai, get_history_ai, get_latest_ai_with_content, get_history_ai_with_content
from .news_stocks import insert as insert_news_stocks, get_by_importance, exists as news_stocks_exists, delete_by_importance as delete_news_stocks_by_importance, get_processed_importance_ids, update_d1_d2_d3_batch, get_recent_stocks, get_recent_stocks_with_created, get_batch_by_importance  # noqa: E501
from .subscription_db import (
    cancel_active_subscription, cancel_subscription_full,
    activate_subscription, activate_subscription_pending,
    get_active_subscription, mark_order_expired,
    create_order, get_order, update_order_paid, get_orders_by_user,
)

__all__ = [
    # connection
    "get_conn",
    "put_conn",
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
    "get_failed_batch",
    "delete_by_id",
    "update_content",
    "batch_insert",
    # importance
    "insert_importance",
    "get_recent",
    "get_recent_by_score",
    "get_latest_batch",
    "get_max_batch_id",
    "get_top_news_by_batch",
    "get_positive_by_date",
    "get_latest_importance_date",
    "update_publish_sector_values",
    "batch_update_publish_sector_values",
    # sectors
    "normalize",
    "fuzzy_match",
    "search",
    "sync_from_iwencai",
    "sectors_count",
    "upsert_sector",
    # sector_indices
    "save_sector_indices",
    "get_sector_indices",
    # orders
    "create_order",
    "get_order",
    "update_order_paid",
    "get_orders_by_user",
    # admin_db
    "list_users",
    "get_user_detail",
    "update_user_subscription",
    "list_feedbacks",
    "reply_feedback",
    "list_pending_subscriptions",
    "confirm_subscription",
    "update_subscription_level",
    "reject_subscription",
    # news_db
    "query_news",
    "get_news_by_id",
    "query_news_admin",
    "query_primary_sources_admin",
    "get_news_source_name",
    # subscription_db
    "cancel_active_subscription",
    "cancel_subscription_full",
    "activate_subscription",
    "activate_subscription_pending",
    "get_active_subscription",
    "mark_order_expired",
    # news_stocks
    "get_batch_by_importance",
    # importance_ai
    "insert_ai",
    "get_recent_ai",
    "get_latest_ai",
    "get_history_ai",
    "get_latest_ai_with_content",
    "get_history_ai_with_content",
]