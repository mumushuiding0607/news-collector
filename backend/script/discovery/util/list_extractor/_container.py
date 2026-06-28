# _container.py - 列表容器定位
#
# 从目标新闻条目向上遍历 DOM，找到包含整个列表的容器。

import re
from typing import Optional

from bs4 import BeautifulSoup

from ._url import is_news_url

# 列表容器常见 class 模式
_LIST_CONTAINER_PATTERNS = [
    re.compile(r"flex.*flex-col.*gap", re.IGNORECASE),
    re.compile(r"grid.*gap", re.IGNORECASE),
    re.compile(r"(^|\s)news-list(\s|$)", re.IGNORECASE),
    re.compile(r"(^|\s)article-list(\s|$)", re.IGNORECASE),
    re.compile(r"(^|\s)list-container(\s|$)", re.IGNORECASE),
    re.compile(r"(^|\s)news(\s|$).*list", re.IGNORECASE),
    re.compile(r"grid-cols-", re.IGNORECASE),
    re.compile(r"@container.*min-w", re.IGNORECASE),
    re.compile(r"gap-\d+", re.IGNORECASE),
]

# 向上遍历的最大层数
_MAX_DEPTH = 15


def find_list_container(element: BeautifulSoup) -> Optional[BeautifulSoup]:
    """
    向上遍历 DOM 找到新闻列表容器。

    优先级：
    1. 真正包含 element 且是列表的容器（深度最小）
    2. 候选中新闻链接最多的容器
    3. 父元素同级中的列表容器（兜底）
    """
    candidates = []
    current = element.parent
    depth = 0

    for _ in range(_MAX_DEPTH):
        if current is None:
            break
        if is_likely_list_container(current):
            candidates.append((current, depth))
        current = current.parent
        depth += 1

    if candidates:
        containing = [(c, d) for c, d in candidates if contains_element(element, c)]
        if containing:
            return min(containing, key=lambda x: x[1])[0]

        def count_news_links(c):
            return sum(1 for l in c.find_all("a", href=True) if is_news_url(l.get("href", "")))
        return max(candidates, key=lambda x: count_news_links(x[0]))[0]

    return find_sibling_list_container(element)


def is_likely_list_container(element: BeautifulSoup) -> bool:
    """宽松的列表容器判断（≥2 个新闻链接即可）。用于标题逆推场景。"""
    news_links = [l for l in element.find_all("a", href=True) if is_news_url(l.get("href", ""))]
    return len(news_links) >= 2


def is_list_container(element: BeautifulSoup) -> bool:
    """严格判断：≥2 新闻链接 + 命中列表 class 模式，或 ≥10 新闻链接"""
    news_links = [l for l in element.find_all("a", href=True) if is_news_url(l.get("href", ""))]
    if len(news_links) < 2:
        return False

    class_str = get_class_string(element)
    for pat in _LIST_CONTAINER_PATTERNS:
        if pat.search(class_str):
            return True

    # 链接数足够多（≥10），无典型 class 也认为是列表容器
    return len(news_links) >= 10


def find_sibling_list_container(element: BeautifulSoup) -> Optional[BeautifulSoup]:
    """查找父元素同级中的列表容器"""
    parent = element.parent
    if parent is None:
        return None
    for sibling in parent.find_all(recursive=False):
        if sibling == element:
            continue
        if is_list_container(sibling):
            return sibling
    return None


def contains_element(element: BeautifulSoup, container: BeautifulSoup) -> bool:
    """检查 element 是否是 container 的后代"""
    current = element.parent
    while current:
        if current == container:
            return True
        current = current.parent
    return False


def get_class_string(element: BeautifulSoup) -> str:
    """获取元素的 class 属性值（list 或 str）"""
    classes = element.get("class", [])
    if isinstance(classes, list):
        return " ".join(classes)
    return str(classes)