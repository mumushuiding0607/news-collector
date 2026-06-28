# _models.py - 列表提取的数据结构

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class NewsItem:
    """单条新闻数据"""
    title: str = ""
    url: str = ""
    summary: str = ""
    publish_time: str = ""
    source: str = ""
    rank: Optional[int] = None
    item_html: str = ""


@dataclass
class NewsListResult:
    """新闻列表提取结果"""
    news_list: list[NewsItem] = field(default_factory=list)
    list_container_tag: str = ""
    list_container_class: str = ""
    item_tag: str = ""
    item_selector: str = ""
    found_headline: str = ""
    target_url: str = ""