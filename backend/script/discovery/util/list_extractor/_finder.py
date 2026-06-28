# _finder.py - 标题定位
#
# 用标题或关键词在 HTML 中搜索定位目标新闻条目。

import re
from typing import Optional

from bs4 import BeautifulSoup

# 中文 2 字以上、英文 4 字以上作为关键词候选
_CHINESE_KEYWORD_RE = re.compile(r"[一-龥]{2,}")
_ENGLISH_KEYWORD_RE = re.compile(r"[a-zA-Z0-9]{4,}")

# 标题中常见前缀（去除后再抽取关键词）
_PREFIX_PATTERNS = [
    r"^【.*?】", r"^\[.*?\]", r"^#+\s*",
    r"^《.*?》", r"^【.*?】", r"^\d+[、\.、]\s*",
]


def find_element_by_headline(soup: BeautifulSoup, headline: str) -> Optional[BeautifulSoup]:
    """
    用标题在 HTML 中搜索，定位目标元素。

    策略：
    1. 精确匹配 h1/h2/h3/h4/h5/h6 中的完整标题
    2. 模糊匹配包含标题关键词的文本节点（score > 0.6）
    """
    for tag in ["h1", "h2", "h3", "h4", "h5", "h6"]:
        for elem in soup.find_all(tag):
            if elem.get_text(strip=True) == headline:
                return elem

    keywords = extract_keywords(headline)
    if not keywords:
        return None

    best_match = None
    best_score = 0
    for elem in soup.find_all(True):
        text = elem.get_text(strip=True)
        if len(text) < 10 or len(text) > 500:
            continue
        score = calculate_match_score(text, headline, keywords)
        if score > best_score and score > 0.6:
            best_score = score
            best_match = elem

    return best_match


def extract_keywords(headline: str) -> list[str]:
    """从标题中提取关键词（去前缀，最多 5 个）"""
    cleaned = headline
    for pat in _PREFIX_PATTERNS:
        cleaned = re.sub(pat, "", cleaned)

    keywords = _CHINESE_KEYWORD_RE.findall(cleaned) + _ENGLISH_KEYWORD_RE.findall(cleaned)
    return keywords[:5]


def calculate_match_score(text: str, headline: str, keywords: list[str]) -> float:
    """计算文本与标题的匹配分数：完整包含返回 1.0，否则按关键词覆盖率"""
    if headline in text:
        return 1.0
    if not keywords:
        return 0
    matched = sum(1 for kw in keywords if kw in text)
    return matched / len(keywords)