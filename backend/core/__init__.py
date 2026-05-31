"""
core - 后端核心业务逻辑层

提供服务类和数据模型，与 API 路由层分离。
"""

from .news_service import NewsService

__all__ = ["NewsService"]