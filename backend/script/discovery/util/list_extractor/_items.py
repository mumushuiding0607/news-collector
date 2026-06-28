# _items.py - 列表条目提取
#
# 从列表容器中提取每条新闻的标题、URL、摘要、时间、来源、排名。

import re
from typing import Optional

from bs4 import BeautifulSoup

from ._models import NewsItem, NewsListResult
from ._url import get_host, is_news_url

# 匹配 "X分钟前"、"昨天"、"今天"、"HH:MM"
_TIME_TEXT_RE = re.compile(r"(\d+分钟前|昨天|今天|\d+:\d+)")
# 匹配 "XX快讯"、"XX新闻" 等来源标识
_SOURCE_TEXT_RE = re.compile(r"([一-龥a-zA-Z0-9]{2,10}?(?:x24|7x24)?快讯|[一-龥a-zA-Z0-9]{2,10}新闻)")
# 匹配带 background-color 的 div 中纯数字 rank
_RANK_DIV_RE = re.compile(r"background-color")
_RANK_TEXT_RE = re.compile(r"^(\d+)$")


def extract_items_from_list(container: BeautifulSoup, result: NewsListResult) -> list[NewsItem]:
    """
    从列表容器中提取所有新闻条目。

    策略：
    1. 优先取容器直接子元素中的 <a> 链接
    2. 直接子元素不够时，递归找网格/列表布局中的条目
    """
    news_items = _collect_items(container, result.target_url)

    if len(news_items) < 2:
        news_items = _extract_items_from_grid_layout(container, result.target_url)

    result.item_tag = "a"
    result.item_selector = f"{container.name} a[href]"
    return news_items


def extract_news_item_from_link(link: BeautifulSoup) -> Optional[NewsItem]:
    """从单个 <a> 链接元素中提取新闻信息"""
    item = NewsItem()
    item.item_html = str(link)

    title_elem = link.find(["h1", "h2", "h3", "h4", "h5", "h6"])
    item.title = title_elem.get_text(strip=True) if title_elem else link.get_text(strip=True)
    if not item.title or len(item.title) < 5:
        return None

    item.url = link.get("href", "")

    # 摘要：取 link 内第一个长度 >30 的 <p>
    for p in link.find_all("p"):
        text = p.get_text(strip=True)
        if len(text) > 30:
            item.summary = text
            break

    meta = extract_meta_info_from_link(link)
    item.publish_time = meta.get("time", "")
    item.source = meta.get("source", "")
    item.rank = extract_rank_number(link)
    return item


def extract_meta_info_from_link(link: BeautifulSoup) -> dict:
    """从链接元素内部提取时间和来源"""
    meta = {"time": "", "source": ""}
    all_texts = [t.get_text(strip=True) for t in link.find_all(["span", "div"])]

    for text in all_texts:
        m = _TIME_TEXT_RE.search(text)
        if m:
            meta["time"] = m.group(1)
            break

    for text in all_texts:
        m = _SOURCE_TEXT_RE.search(text)
        if m:
            meta["source"] = m.group(1)
            break

    return meta


def extract_rank_number(link: BeautifulSoup) -> Optional[int]:
    """提取新闻排名序号（来自带 background-color 容器内的数字 span）"""
    # 先在 link 内部找
    rank = _find_rank_in(link)
    if rank is not None:
        return rank
    # 再在父容器中找
    parent = link.parent
    if parent:
        return _find_rank_in(parent)
    return None


def _collect_items(container: BeautifulSoup, target_url: str) -> list[NewsItem]:
    """收集容器直接子元素中的 <a> 链接（按域名过滤）"""
    target_host = get_host(target_url)
    items = []
    for link in container.find_all("a", href=True):
        href = link.get("href", "")
        if not is_news_url(href):
            continue
        if target_host and get_host(href) != target_host:
            continue
        item = extract_news_item_from_link(link)
        if item and item.title:
            items.append(item)
    return items


def _extract_items_from_grid_layout(container: BeautifulSoup, target_url: str) -> list[NewsItem]:
    """网格布局兜底：遍历所有层级的 <a> 链接"""
    target_host = get_host(target_url)
    items = []
    for link in container.find_all("a", href=True):
        href = link.get("href", "")
        if not is_news_url(href):
            continue
        if target_host and get_host(href) != target_host:
            continue
        item = extract_news_item_from_link(link)
        if item and item.title:
            items.append(item)
    return items


def _find_rank_in(scope: BeautifulSoup) -> Optional[int]:
    for div in scope.find_all("div", style=_RANK_DIV_RE):
        span = div.find("span")
        if span:
            text = span.get_text(strip=True)
            m = _RANK_TEXT_RE.match(text)
            if m:
                return int(m.group(1))
    return None