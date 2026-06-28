# _content.py - 正文发现相关 phase
import asyncio
from urllib.parse import urljoin

from script.discovery.content_discovery import discover_content_config
from script.discovery.html_cleaner import clean_article_html
from script.discovery.list_discovery import log
from script.discovery.util.html_fetch import fetch_article_html as _fetch_article_html_async


def discover_content_with_policy(
    article_url: str | None,
    existing_content_extract: dict | None,
    skip_article_crawler: bool,
    force_relearn: bool,
    base_url: str,
    article_title: str = "",
) -> dict:
    """Step 4: 正文发现，根据已有配置、skip_article_crawler、force_relearn 决定保留/覆盖"""
    if skip_article_crawler:
        log("[统一学习] list_complete=True，跳过正文学习")
        return _wrap_existing(existing_content_extract)

    if existing_content_extract and not force_relearn:
        log(f"[统一学习] 保留已有正文配置: selector={existing_content_extract.get('selector')}")
        return _wrap_existing(existing_content_extract)

    if not article_url:
        log("[统一学习] 无文章URL可学习正文配置")
        return _wrap_existing(existing_content_extract)

    if article_url.startswith("/"):
        article_url = urljoin(base_url, article_url)

    log(f"[统一学习] 抓取文章页: {article_url}")
    _, article_html = asyncio.run(_fetch_article_html_async(article_url))
    if not article_html:
        log("[统一学习] 文章页抓取失败")
        return _wrap_existing(existing_content_extract)

    log("[统一学习] 文章页抓取成功，开始正文发现...")
    content_config = discover_content_config(article_url, article_html, headline=article_title)
    if content_config:
        log(f"[统一学习] 正文发现成功: {content_config.get('content_extract', {}).get('selector', 'N/A')}")
        return content_config

    suffix = "，保留已有配置" if existing_content_extract else ""
    log(f"[统一学习] 正文发现返回空配置{suffix}")
    return _wrap_existing(existing_content_extract)


def _wrap_existing(existing: dict | None) -> dict:
    if existing:
        return {"content_extract": existing}
    return {}