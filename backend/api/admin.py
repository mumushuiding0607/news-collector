"""
Admin API - 后台管理

只负责路由和参数校验，业务逻辑委托给 core.admin_service。
所有管理接口都需要管理员权限验证。
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from backend.core.admin_service import (
    get_users, get_user_detail,
    update_user_subscription_service, update_subscription_level,
    get_feedbacks, reply_feedback,
    get_pending_subscriptions, confirm_subscription,
    get_crawl_configs_service,
    confirm_crawl_config_service, unconfirm_crawl_config_service,
    remove_crawl_config_service, update_crawl_config_service,
    create_crawl_config_service,
    generate_anomaly_summary_service,
    get_anomaly_news_service,
    delete_anomaly_news_service,
    delete_anomaly_news_before_date_service,
    delete_summary_before_date_service,
    mark_anomaly_processed_service,
    mark_all_anomaly_processed_service,
    get_comments_service,
    get_feedback_summary_service,
    delete_primary_sources_by_date_service,
    delete_primary_sources_by_date_before_service,
    delete_importance_by_score_service,
)
from backend.api._auth import get_user_email, require_admin

router = APIRouter(prefix="/admin", tags=["管理"])


class UpdateLevelRequest(BaseModel):
    level: str
    days: int


class ReplyRequest(BaseModel):
    reply: str


@router.get("/users")
def list_users(request: Request, level: str | None = None, phone: str | None = None, page: int = 1, limit: int = 20):
    require_admin(request)
    return get_users(level=level, phone=phone, page=page, limit=limit)


@router.get("/users/{user_id}")
def get_user(request: Request, user_id: int):
    require_admin(request)
    return get_user_detail(user_id)


@router.post("/users/{user_id}/level")
def set_user_level(request: Request, user_id: int, body: UpdateLevelRequest):
    require_admin(request)
    return update_user_subscription_service(user_id, body.level, body.days)


@router.get("/feedbacks")
def list_feedbacks(request: Request, page: int = 1, limit: int = 20):
    require_admin(request)
    return get_feedbacks(page=page, limit=limit)


@router.post("/feedbacks/{feedback_id}/reply")
def reply(request: Request, feedback_id: int, body: ReplyRequest):
    require_admin(request)
    return reply_feedback(feedback_id, body.reply)


# ============ 订阅管理 ============
@router.get("/subscriptions/pending")
def list_pending_subscriptions(request: Request):
    """获取待确认的订阅用户列表"""
    require_admin(request)
    return {"list": get_pending_subscriptions()}


@router.post("/subscriptions/{user_id}/confirm")
def confirm_user_subscription(request: Request, user_id: int):
    """确认用户的订阅状态"""
    require_admin(request)
    return confirm_subscription(user_id)


@router.post("/subscriptions/{user_id}/level")
def update_user_subscription_level(request: Request, user_id: int, body: UpdateLevelRequest):
    """修改用户订阅等级（管理员操作）"""
    require_admin(request)
    return update_subscription_level(user_id, body.level, body.days)


class RejectRequest(BaseModel):
    reason: str = ""


class UpdateSourcePrepareRequest(BaseModel):
    source_name: str | None = None
    url: str | None = None
    status: str | None = None


@router.post("/subscriptions/{user_id}/reject")
def reject_user_subscription(request: Request, user_id: int, body: RejectRequest):
    """
    拒绝用户订阅申请：
    1. 发送邮件要求上传付款凭证
    2. 将订阅状态改为 proof_requested，订单改回 pending
    """
    require_admin(request)
    from core.subscription_service import send_rejection_email
    from script.db import list_pending_subscriptions, reject_subscription as db_reject_subscription
    # 找出该用户的 pending 记录对应的 level
    pending = list_pending_subscriptions()
    level = "pro"
    for p in pending:
        if p.get("user_id") == user_id:
            level = p.get("level", "pro")
            break
    # 发送邮件（失败也继续更新状态）
    email_ok = send_rejection_email(user_id, level, body.reason)
    # 更新数据库状态
    db_reject_subscription(user_id, body.reason)
    return {
        "ok": True,
        "email_sent": email_ok,
        "message": "已拒绝并发送邮件" if email_ok else "已拒绝，邮件发送失败请检查配置",
    }


# ============ source_crawl_configs 管理 ============


class CreateCrawlConfigRequest(BaseModel):
    name: str
    url_norm: str


@router.post("/crawl-configs")
def create_crawl_config(request: Request, body: CreateCrawlConfigRequest, news_type: str = "stock"):
    """新增数据源配置"""
    require_admin(request)
    from script.db.db_selector import ensure_db
    ensure_db(news_type)
    return create_crawl_config_service(name=body.name, url_norm=body.url_norm)


@router.get("/crawl-configs")
def list_crawl_configs(request: Request, checked: int | None = None, page: int = 1, limit: int = 50,
                      news_type: str = "stock"):
    """分页查询数据源配置（checked: 0=未确认, 1=已确认, None=全部）"""
    require_admin(request)
    from script.db.db_selector import ensure_db
    ensure_db(news_type)
    return get_crawl_configs_service(checked=checked, page=page, limit=limit)


@router.get("/crawl-configs/source_names")
def list_source_names(request: Request, news_type: str = "stock"):
    """获取所有数据源名称列表（用于筛选）"""
    require_admin(request)
    from script.db.db_selector import ensure_db
    ensure_db(news_type)
    from script.db.admin_db import list_crawl_config_names
    names = list_crawl_config_names()
    return {"source_names": names}


@router.post("/crawl-configs/{config_id}/confirm")
def confirm_crawl_config(request: Request, config_id: int, news_type: str = "stock"):
    """确认数据源配置（checked=1）"""
    require_admin(request)
    from script.db.db_selector import ensure_db
    ensure_db(news_type)
    return confirm_crawl_config_service(config_id)


@router.post("/crawl-configs/{config_id}/unconfirm")
def unconfirm_crawl_config(request: Request, config_id: int, news_type: str = "stock"):
    """取消确认数据源配置（checked=0）"""
    require_admin(request)
    from script.db.db_selector import ensure_db
    ensure_db(news_type)
    return unconfirm_crawl_config_service(config_id)


@router.delete("/crawl-configs/{config_id}")
def delete_crawl_config(request: Request, config_id: int, news_type: str = "stock"):
    """删除数据源配置"""
    require_admin(request)
    from script.db.db_selector import ensure_db
    ensure_db(news_type)
    return remove_crawl_config_service(config_id)


class UpdateCrawlConfigRequest(BaseModel):
    name: str | None = None
    url_norm: str | None = None
    list_config: str | None = None
    content_extract: str | None = None
    crawl_order: int | None = None
    is_flash: int | None = None


@router.put("/crawl-configs/{config_id}")
def update_crawl_config(request: Request, config_id: int, body: UpdateCrawlConfigRequest, news_type: str = "stock"):
    """更新数据源配置"""
    require_admin(request)
    from script.db.db_selector import ensure_db
    ensure_db(news_type)
    return update_crawl_config_service(
        config_id,
        name=body.name,
        url_norm=body.url_norm,
        list_config=body.list_config,
        content_extract=body.content_extract,
        crawl_order=body.crawl_order,
        is_flash=body.is_flash,
    )


# ============ 原始数据管理 ============


@router.get("/primary_sources/{news_id}")
def get_primary_source_detail(request: Request, news_id: int):
    """获取原始数据新闻详情"""
    require_admin(request)
    from script.db.primary_source import get_by_id
    news = get_by_id(news_id)
    if not news:
        raise HTTPException(status_code=404, detail="记录不存在")
    return news


@router.delete("/primary_sources/by_date")
def delete_primary_sources_by_date(request: Request, date: str):
    """
    删除指定抓取日期的原始数据新闻。
    date 格式：YYYY-MM-DD，默认当天。
    """
    require_admin(request)
    return delete_primary_sources_by_date_service(date)


@router.delete("/primary_sources/before_date")
def delete_primary_sources_by_date_before(request: Request, date: str):
    """
    删除指定日期之前的所有原始数据新闻。
    date 格式：YYYY-MM-DD，删除该日期之前（不含当天）的所有记录。
    """
    require_admin(request)
    return delete_primary_sources_by_date_before_service(date)


@router.delete("/news/by_score")
def delete_importance_by_score(request: Request, score: float):
    """
    删除评分低于指定分数的重要新闻。
    score：低于此分数的新闻将被删除。
    """
    require_admin(request)
    return delete_importance_by_score_service(score)


@router.delete("/anomaly-news/before_date")
def delete_anomaly_news_before_date(request: Request, date: str):
    """删除指定日期之前的所有异动消息"""
    require_admin(request)
    return delete_anomaly_news_before_date_service(date)


# ============ 异动简报 ============


@router.get("/anomaly/summary")
def get_anomaly_summary(request: Request, date: str | None = None, limit: int = 200):
    """生成异动简报（指定日期或不指定则取最新日期）"""
    require_admin(request)
    return generate_anomaly_summary_service(date_str=date, limit=limit)


# ============ 简报管理（统一） ============


@router.get("/summaries")
def list_summaries_admin(
    request: Request,
    type: str | None = None,
    page: int = 1,
    limit: int = 20,
):
    """分页查询简报列表，支持按 type 过滤"""
    require_admin(request)
    from script.db.anomaly_summary_db import list_summaries_by_date
    return list_summaries_by_date(page=page, limit=limit, summary_type=type)


@router.delete("/summaries/before_date")
def delete_summaries_before_date(request: Request, date: str):
    """删除指定日期之前的所有简报"""
    require_admin(request)
    return delete_summary_before_date_service(date)


@router.get("/summary/{date}")
def get_summary_by_date_admin(
    request: Request,
    date: str,
    type: str | None = None,
):
    """获取指定日期的简报，支持 type 过滤"""
    require_admin(request)
    from script.db.anomaly_summary_db import get_summary_by_date_and_type, get_summary
    if type:
        return get_summary_by_date_and_type(date, type) or {}
    return get_summary(date_str=date) or {}


# ============ 异动消息管理 ============


@router.get("/anomaly-news")
def list_anomaly_news(
    request: Request,
    sourceName: str | None = Query(None, alias="sourceName"),
    title: str | None = None,
    keyword: str | None = None,
    processed: int | None = None,
    page: int = 1,
    limit: int = 20,
):
    """分页查询异动消息列表，支持关键词搜索（模糊匹配 title 和 content）"""
    require_admin(request)
    return get_anomaly_news_service(source_name=sourceName, title=title, keyword=keyword, processed=processed, page=page, limit=limit)


@router.delete("/anomaly-news/{news_id}")
def delete_anomaly_news(request: Request, news_id: int):
    """删除异动消息"""
    require_admin(request)
    return delete_anomaly_news_service(news_id)


@router.post("/anomaly-news/{news_id}/processed")
def mark_anomaly_processed(request: Request, news_id: int):
    """标记异动消息为已处理"""
    require_admin(request)
    return mark_anomaly_processed_service(news_id)


@router.post("/anomaly-news/mark-all-processed")
def mark_all_anomaly_processed(request: Request):
    """标记所有异动消息为已处理"""
    require_admin(request)
    return mark_all_anomaly_processed_service()


# ============ 评论管理 ============


@router.get("/comments")
def list_comments(request: Request, news_id: int | None = None, page: int = 1, limit: int = 20):
    """分页查询评论列表"""
    require_admin(request)
    return get_comments_service(news_id=news_id, page=page, limit=limit)


@router.get("/feedback-summary")
def list_feedback_summary(request: Request, news_id: int | None = None, page: int = 1, limit: int = 20):
    """分页查询用户反馈汇总"""
    require_admin(request)
    return get_feedback_summary_service(news_id=news_id, page=page, limit=limit)