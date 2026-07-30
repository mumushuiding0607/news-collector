"""
api/ - API Router 统一出口

所有路由在此集中注册，主模块只做 lifespan 管理。
"""

from backend.api.admin import router as admin_router
from backend.api.news import router as news_router
from .auth import router as auth_router
from backend.api.subscription import router as subscription_router
from backend.api.feedback import router as feedback_router
from backend.api.feedback import comments_router
from backend.api.config_api import router as config_router
from backend.api.schedule_api import router as schedule_router
from backend.api.log_api import router as log_router
from backend.api.wechat_token import router as wechat_router

__all__ = [
    "admin_router",
    "news_router",
    "auth_router",
    "subscription_router",
    "feedback_router",
    "comments_router",
    "config_router",
    "schedule_router",
    "log_router",
    "wechat_router",
]

# 默认 router（向后兼容）
router = news_router