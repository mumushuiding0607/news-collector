"""
API Routes - News endpoints

使用 backend/core/NewsService 提供新闻数据接口。
缓存和业务逻辑已在服务层处理。
"""
from fastapi import APIRouter

from backend.core.news_service import NewsService

router = APIRouter()


@router.get("/news/hot")
def get_news_hot():
    """获取热点新闻（当日得分最高的新闻）"""
    return NewsService.get_hot_news(limit=10)


@router.get("/news/latest")
def get_news_latest():
    """获取最新批次的高分新闻（前10条）"""
    return NewsService.get_latest_news(limit=10)


@router.get("/news/history")
def get_news_history(days: int = 3):
    """获取历史新闻"""
    return NewsService.get_history_news(days=days, limit=50)


@router.get("/news")
def get_news():
    """获取最新批次的高分新闻（兼容旧版）"""
    return NewsService.get_latest_news(limit=10)


@router.get("/news/detail/{news_id}")
def get_news_detail(news_id: int):
    """获取单条新闻详情"""
    news = NewsService.get_news_detail(news_id)
    if not news:
        return {"error": "News not found"}
    return news


def update_news_cache():
    """更新新闻缓存（在新闻采集完成后调用）"""
    return NewsService.update_cache()
