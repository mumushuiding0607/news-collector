"""
admin_service.py - 后台管理业务服务

从 api/admin.py 提取的业务逻辑，包括：
- 用户列表 / 明细查询
- 用户订阅等级变更
- 反馈列表 / 回复
- 管理员验证
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from script.db import (
    list_users, get_user_detail, update_user_subscription,
    list_feedbacks, reply_feedback,
    list_pending_subscriptions, confirm_subscription, update_subscription_level,
)
from script.db.admin_db import (
    list_crawl_configs, set_crawl_config_checked, delete_crawl_config, update_crawl_config,
    create_crawl_config,
)
from script.db.primary_source import delete_by_fetched_date
from script.db.anomaly_news import (
    get_anomaly_news_by_date, get_latest_anomaly_date, get_anomaly_news,
    get_anomaly_news_by_source_latest_date,
)
from script.anomaly_news.summary import generate as _generate_summary

_ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "181457121@qq.com")


def is_admin_email(email: str | None) -> bool:
    """检查邮箱是否为管理员"""
    return bool(email and email.lower() == _ADMIN_EMAIL.lower())


def get_users(level: str | None = None, phone: str | None = None, page: int = 1, limit: int = 20):
    """分页查询用户列表"""
    return list_users(level=level, phone=phone, page=page, limit=limit)


def get_user_detail_service(user_id: int):
    """获取用户详情"""
    result = get_user_detail(user_id)
    if not result:
        raise ValueError("用户不存在")
    return result


def update_user_subscription_service(user_id: int, level: str, days: int):
    """变更用户订阅等级"""
    now = datetime.now()
    expire_at = (now + __import__("datetime").timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S") if days > 0 else None
    return update_user_subscription(user_id, level, days, expire_at)


def get_feedbacks(page: int = 1, limit: int = 20):
    """分页查询反馈列表"""
    return list_feedbacks(page=page, limit=limit)


def reply_feedback_service(feedback_id: int, reply: str):
    """回复反馈"""
    return reply_feedback(feedback_id, reply)


def get_pending_subscriptions_service():
    """获取待确认的订阅用户"""
    return list_pending_subscriptions()


def confirm_subscription_service(user_id: int):
    """确认用户订阅"""
    return confirm_subscription(user_id)


def get_pending_subscriptions():
    """获取待确认的订阅用户"""
    return get_pending_subscriptions_service()


def update_subscription_level_service(user_id: int, level: str, days: int):
    """修改用户订阅等级"""
    now = datetime.now()
    expire_at = (now + __import__("datetime").timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S") if days > 0 else None
    return update_subscription_level(user_id, level, expire_at)


# ============ source_crawl_configs 管理 ============


def get_crawl_configs_service(checked: int | None = None, page: int = 1, limit: int = 50):
    """分页查询数据源配置"""
    return list_crawl_configs(checked=checked, page=page, limit=limit)


def confirm_crawl_config_service(config_id: int):
    """确认数据源配置（checked=1）"""
    return set_crawl_config_checked(config_id, 1)


def unconfirm_crawl_config_service(config_id: int):
    """取消确认数据源配置（checked=0）"""
    return set_crawl_config_checked(config_id, 0)


def remove_crawl_config_service(config_id: int):
    """删除数据源配置"""
    return delete_crawl_config(config_id)


def update_crawl_config_service(config_id: int, name: str | None = None, url_norm: str | None = None,
                                list_config: str | None = None, content_extract: str | None = None,
                                crawl_order: int | None = None, is_flash: int | None = None):
    """更新数据源配置"""
    return update_crawl_config(config_id, name=name, url_norm=url_norm, list_config=list_config,
                              content_extract=content_extract, crawl_order=crawl_order, is_flash=is_flash)


def create_crawl_config_service(name: str, url_norm: str) -> dict:
    """新增数据源配置"""
    return create_crawl_config(name=name, url_norm=url_norm)


def generate_anomaly_summary_service(date_str: str | None = None, limit: int = 200) -> dict:
    """生成异动简报（委托给 script/anomaly_summary.py）"""
    return _generate_summary(date_str=date_str, limit=limit)


def get_anomaly_news_service(source_name: str | None = None, title: str | None = None, processed: int | None = None, page: int = 1, limit: int = 20):
    """分页查询异动消息列表"""
    from script.db.anomaly_news import get_anomaly_news as _get_anomaly_news, count_anomaly_news as _count_anomaly_news
    offset = (page - 1) * limit
    total = _count_anomaly_news(source_name=source_name, title=title, processed=processed)
    rows = _get_anomaly_news(source_name=source_name, title=title, limit=limit, offset=offset, processed=processed)
    return {
        "list": [{"id": r[0], "title": r[1], "url": r[2], "publish_time": r[3], "source_name": r[4], "processed": r[5], "created_at": r[6]} for r in rows],
        "total": total,
        "page": page,
        "limit": limit,
    }


def delete_anomaly_news_service(news_id: int) -> dict:
    """删除异动消息"""
    from script.db.anomaly_news import delete_anomaly_news as _delete
    ok = _delete(news_id)
    return {"deleted": ok, "id": news_id}


def mark_anomaly_processed_service(news_id: int) -> dict:
    """切换异动消息处理状态：已处理→未处理，未处理→已处理"""
    from script.db.anomaly_news import toggle_processed as _toggle
    ok, processed = _toggle(news_id)
    return {"ok": ok, "id": news_id, "processed": processed}


def mark_all_anomaly_processed_service() -> dict:
    """标记所有异动消息为已处理"""
    from script.db.anomaly_news import mark_all_processed as _mark_all
    count = _mark_all()
    return {"marked": count}


# ============ 原始数据管理 ============


def delete_primary_sources_by_date_service(date_str: str) -> dict:
    """删除指定抓取日期的原始数据，返回删除数量"""
    deleted = delete_by_fetched_date(date_str)
    return {"deleted": deleted, "date": date_str}


# ============ 评论管理 ============


def get_comments_service(news_id: int | None = None, page: int = 1, limit: int = 20):
    """分页查询评论列表"""
    from script.db import get_conn, put_conn
    conn = get_conn()
    try:
        offset = (page - 1) * limit
        if news_id:
            count_row = conn.execute("SELECT COUNT(*) FROM comments WHERE news_id = ?", (news_id,)).fetchone()
            rows = conn.execute("""
                SELECT c.id, c.news_id, c.user_id, c.content, c.processed, c.created_at,
                       i.title as news_title
                FROM comments c
                LEFT JOIN importance i ON c.news_id = i.id
                WHERE c.news_id = ?
                ORDER BY c.created_at DESC
                LIMIT ? OFFSET ?
            """, (news_id, limit, offset)).fetchall()
        else:
            count_row = conn.execute("SELECT COUNT(*) FROM comments").fetchone()
            rows = conn.execute("""
                SELECT c.id, c.news_id, c.user_id, c.content, c.processed, c.created_at,
                       i.title as news_title
                FROM comments c
                LEFT JOIN importance i ON c.news_id = i.id
                ORDER BY c.created_at DESC
                LIMIT ? OFFSET ?
            """, (limit, offset)).fetchall()
        total = count_row[0] if count_row else 0
        return {
            "total": total,
            "page": page,
            "limit": limit,
            "list": [
                {"id": r[0], "news_id": r[1], "user_id": r[2], "content": r[3],
                 "processed": r[4], "created_at": r[5], "news_title": r[6]}
                for r in rows
            ]
        }
    finally:
        put_conn(conn)


def get_feedback_summary_service(news_id: int | None = None, page: int = 1, limit: int = 20):
    """分页查询用户反馈汇总"""
    from script.db import get_conn, put_conn
    conn = get_conn()
    try:
        offset = (page - 1) * limit
        if news_id:
            count_row = conn.execute("SELECT COUNT(*) FROM comment_feedback WHERE news_id = ?", (news_id,)).fetchone()
            rows = conn.execute("""
                SELECT f.id, f.news_id, f.feedback_content, f.created_at,
                       i.title as news_title
                FROM comment_feedback f
                LEFT JOIN importance i ON f.news_id = i.id
                WHERE f.news_id = ?
                ORDER BY f.created_at DESC
                LIMIT ? OFFSET ?
            """, (news_id, limit, offset)).fetchall()
        else:
            count_row = conn.execute("SELECT COUNT(*) FROM comment_feedback").fetchone()
            rows = conn.execute("""
                SELECT f.id, f.news_id, f.feedback_content, f.created_at,
                       i.title as news_title
                FROM comment_feedback f
                LEFT JOIN importance i ON f.news_id = i.id
                ORDER BY f.created_at DESC
                LIMIT ? OFFSET ?
            """, (limit, offset)).fetchall()
        total = count_row[0] if count_row else 0
        return {
            "total": total,
            "page": page,
            "limit": limit,
            "list": [
                {"id": r[0], "news_id": r[1], "feedback_content": r[2],
                 "created_at": r[3], "news_title": r[4]}
                for r in rows
            ]
        }
    finally:
        put_conn(conn)