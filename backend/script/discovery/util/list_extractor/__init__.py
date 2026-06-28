"""
list_extractor - 基于标题定位的新闻列表提取器

从渲染后的HTML中，根据用户提供的标题/关键字逆推新闻列表位置，
并提取列表中所有新闻的标题、摘要、发布时间等内容。

使用方法：
    from script.discovery.util.list_extractor import extract_news_list_from_rendered_html

    html = open("test/10jqka.com.cn.html", "r", encoding="utf-8").read()
    headline = "工信部：到2028年人工智能与信息通信初步构建融合互促的创新发展格局"

    result = extract_news_list_from_rendered_html(html, headline)
"""
from __future__ import annotations

from typing import Optional

from bs4 import BeautifulSoup

from ._container import find_list_container, get_class_string
from ._finder import find_element_by_headline
from ._items import extract_items_from_list
from ._models import NewsItem, NewsListResult
from ._url import get_host, is_news_url

__all__ = [
    "NewsItem",
    "NewsListResult",
    "extract_news_list_from_rendered_html",
    "extract_from_file",
    "extract_as_dict",
]


def extract_news_list_from_rendered_html(
    html: str,
    headline: str,
    max_search_length: int = 500000,
) -> NewsListResult:
    """
    从渲染后的HTML中，根据标题逆推新闻列表并提取内容。

    算法步骤：
    1. 用标题关键词在HTML中搜索，定位目标新闻条目
    2. 向上遍历DOM找到新闻列表容器
    3. 提取列表中所有新闻条目

    Args:
        html: 渲染后的HTML内容
        headline: 用户提供的标题或关键字（部分匹配）
        max_search_length: 最大搜索长度（避免处理过大HTML）

    Returns:
        NewsListResult
    """
    try:
        from bs4 import BeautifulSoup  # noqa: F811
    except ImportError:
        raise ImportError("需要安装 beautifulsoup4: pip install beautifulsoup4")

    result = NewsListResult(found_headline=headline)

    # HTML 过长时，先判断标题是否在范围内，避免遗漏
    if len(html) > max_search_length:
        if headline not in html[:max_search_length]:
            headline_pos = html.find(headline)
            if headline_pos > 0:
                start = max(0, headline_pos - 10000)
                html = html[start:start + max_search_length]

    soup = BeautifulSoup(html, "html.parser")

    # Step 1: 定位目标新闻条目
    target_element = find_element_by_headline(soup, headline)
    if target_element is None:
        return result

    # 记录头条 URL（用于域名过滤）
    if target_element.name == "a" and target_element.get("href"):
        result.target_url = target_element.get("href", "")
    else:
        parent_a = target_element.find_parent("a")
        if parent_a:
            result.target_url = parent_a.get("href", "")

    # Step 2: 找到列表容器
    list_container = find_list_container(target_element)
    if list_container is None:
        return result

    result.list_container_tag = list_container.name
    result.list_container_class = get_class_string(list_container)

    # Step 3: 提取所有条目
    result.news_list = extract_items_from_list(list_container, result)
    return result


def extract_from_file(file_path: str, headline: str) -> NewsListResult:
    """从 HTML 文件中提取新闻列表"""
    with open(file_path, "r", encoding="utf-8") as f:
        html = f.read()
    return extract_news_list_from_rendered_html(html, headline)


def extract_as_dict(file_path: str, headline: str) -> dict:
    """从 HTML 文件中提取新闻列表，以字典形式返回"""
    result = extract_from_file(file_path, headline)
    return {
        "news_list": [
            {
                "title": item.title,
                "url": item.url,
                "summary": item.summary,
                "publish_time": item.publish_time,
                "source": item.source,
                "rank": item.rank,
            }
            for item in result.news_list
        ],
        "list_info": {
            "container_tag": result.list_container_tag,
            "container_class": result.list_container_class,
            "item_tag": result.item_tag,
            "item_selector": result.item_selector,
            "found_headline": result.found_headline,
        },
    }