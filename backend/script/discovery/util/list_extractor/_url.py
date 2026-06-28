# _url.py - URL 判断工具
#
# 提供新闻 URL 判定、域名提取等基础工具，被 finder/container/items 等模块复用。

import re
from urllib.parse import urlparse

# 排除规则：图片、CSS、JS、锚点等非新闻链接
_EXCLUDE_PATTERNS = [
    r"\.(jpg|jpeg|png|gif|svg|webp|css|js)(\?|$)",
    r"^javascript:",
    r"^#",
]

# 新闻链接路径特征：含 /news/、/article/、日期路径 /YYYYMMDD/、.shtml、.html
_NEWS_PATTERNS = [
    r"/news/",
    r"/article/",
    r"/\d{8}/",
    r"\.shtml",
    r"\.html",
]

_EXCLUDE_RE = re.compile("|".join(_EXCLUDE_PATTERNS), re.IGNORECASE)
_NEWS_RE = re.compile("|".join(_NEWS_PATTERNS))


def is_news_url(url: str) -> bool:
    """判断 URL 是否是新闻链接"""
    if not url:
        return False
    if _EXCLUDE_RE.search(url):
        return False
    return bool(_NEWS_RE.search(url))


def get_host(url: str) -> str:
    """从 URL 提取域名（netloc）"""
    return urlparse(url).netloc if url else ""