"""
models - Pydantic 数据模型

定义 API 请求/响应的数据结构。
"""

from typing import Optional, List
from pydantic import BaseModel


class NewsItem(BaseModel):
    """新闻条目"""
    id: int
    title: str
    url: str
    source_name: str
    publish_time: Optional[str] = None
    summary: Optional[str] = None
    related_sectors: Optional[str] = None
    importance_score: int = 0
    reason: Optional[str] = None
    direction: Optional[str] = None
    intensity: Optional[int] = None
    expected_change: Optional[str] = None
    duration: Optional[str] = None
    expectation_level: Optional[str] = None
    market_mode: Optional[str] = None
    max_sector_rise: Optional[float] = None
    publish_sector_values: Optional[str] = None
    current_sector_values: Optional[str] = None
    created_at: str


class NewsResponse(BaseModel):
    """新闻列表响应"""
    data: List[NewsItem]
    batch_time: Optional[str]
    count: int