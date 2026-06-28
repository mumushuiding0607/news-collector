# validation.py - 新闻样本验证工具
#
# 验证新闻 URL 和样本的有效性。
#
# 使用方式：
#   from script.discovery.util.validation import is_valid_news_url, is_valid_news_sample

import re

# 默认新闻 URL 域名模式（CCTV/人民网等）
DEFAULT_NEWS_DOMAIN_RE = re.compile(r'https?://(tv\.cctv|news\.|www\.)[\w\-\.]+/\d{4}/\d{2}/\d{2}/')

# Minimum URL length for valid news URL
MIN_URL_LENGTH = 20


def is_valid_news_url(url: str, domain_re=None) -> bool:
    """
    验证是否为有效的新闻 URL。

    检查：
    - URL 长度 >= 20
    - 不含 HTML 残片（html?、<a、javascript）
    - 匹配新闻 URL 域名+日期路径格式

    Args:
        url: 待验证的 URL
        domain_re: 可选，域名正则，默认使用 DEFAULT_NEWS_DOMAIN_RE

    Returns:
        True 表示有效
    """
    if not url or len(url) < MIN_URL_LENGTH:
        return False
    if 'html?' in url or '<a' in url or url.startswith('javascript'):
        return False
    if domain_re is None:
        domain_re = DEFAULT_NEWS_DOMAIN_RE
    return bool(domain_re.match(url))


def is_valid_news_sample(news, domain_re=None) -> bool:
    """
    验证新闻样本字典或对象是否有效。

    检查：
    - 有 url 且通过 is_valid_news_url
    - 有 title 且不为 HTML 代码，长度 >= 5

    Args:
        news: {"url": ..., "title": ...} 字典或 NewsItem 对象
        domain_re: 可选，域名正则

    Returns:
        True 表示有效
    """
    # 支持 dict 或有 url/title 属性的对象
    if hasattr(news, 'url'):
        url = getattr(news, 'url', '')
        title = getattr(news, 'title', '')
    else:
        url = news.get("url", "") if isinstance(news, dict) else ""
        title = news.get("title", "") if isinstance(news, dict) else ""

    if not is_valid_news_url(url, domain_re):
        return False
    if '<a' in title or '<span' in title or len(title) < 5:
        return False
    return True