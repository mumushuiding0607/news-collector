"""
urlutil.py - URL 处理工具
"""


def normalize_url(url: str) -> str:
    """URL 标准化：去除末尾 /、统一 http/https -> http"""
    url = url.rstrip("/")
    if url.startswith("https://"):
        url = "http://" + url[8:]
    return url
