"""
raw_fetch.py - 原始 HTTP 获取器

用于获取原始 HTML 源码（不走 headless browser），
适用于 SSR 页面中嵌入的 JSON 数据检测。
"""
from __future__ import annotations

import ssl
import urllib.request


def fetch_raw_html(url: str, timeout: int = 10) -> str:
    """
    使用原始 HTTP/HTTPS 请求获取 HTML 源码。

    与 crawl4ai 不同，这个方法不执行 JavaScript，
    直接获取服务器返回的原始 HTML（可能包含嵌入式 JSON）。

    Args:
        url: 目标 URL
        timeout: 超时秒数

    Returns:
        HTML 源码字符串，获取失败返回空字符串
    """
    try:
        # 创建 SSL context（忽略证书问题）
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            },
        )

        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as response:
            raw = response.read()
            content_type = response.headers.get("Content-Type", "")
            if "charset=" in content_type:
                charset = content_type.split("charset=")[-1].split(";")[0].strip().lower()
                try:
                    return raw.decode(charset)
                except (UnicodeDecodeError, LookupError):
                    pass
            # header charset 失败时用 chardet 自动检测
            import chardet
            detected = chardet.detect(raw)
            real_charset = (detected.get("encoding") or "utf-8").lower()
            return raw.decode(real_charset, errors="replace")

    except Exception:
        return ""


def fetch_with_retry(url: str, max_retries: int = 3, retry_delay: int = 3) -> str:
    """
    带重试的原始 HTML 获取。

    Args:
        url: 目标 URL
        max_retries: 最大重试次数
        retry_delay: 重试间隔秒数

    Returns:
        HTML 源码字符串，获取失败返回空字符串
    """
    import time

    for attempt in range(max_retries):
        html = fetch_raw_html(url)
        if html:
            return html
        if attempt < max_retries - 1:
            time.sleep(retry_delay)
    return ""