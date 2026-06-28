"""
news_fetch.py - 通用新闻获取接口

结合 source_crawl_configs.list_config 获取新闻。
不需要提前学习配置（配置不存在时使用通用方式获取）。
"""
import asyncio
import json
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from script.bootstrap import *
from script.common.jsonutil import parse_json_field
from script.log import log as _log
from script.db.sources_db import list_sources_with_configs
from script.discovery.list_discovery import _fetch_html
from script.discovery.article_link_extractor import extract_article_links
from script.discovery.raw_fetch import fetch_raw_html
from script.discovery.embedded_json import find_embedded_json, extract_news_items


def log(msg: str):
    _log("news_fetch", msg)


def fetch_news_universal(url: str, limit: int = 20) -> dict:
    """
    通用新闻获取接口。

    策略：
    1. 有 list_config 配置 → 根据 type 获取（api/raw/html）
    2. 无配置 → 使用 crawl4ai + extract_article_links 通用方式

    Args:
        url: 新闻数据源 URL
        limit: 返回条数限制

    Returns:
        dict: {
            "ok": bool,
            "source_name": str,
            "source_type": str,
            "count": int,
            "news": list[dict]  # title/url/publish_time/summary
        }
    """
    # Step 1: 检查是否有 list_config
    config = _get_source_config(url)

    if config and config.get("list_config"):
        log(f"[获取] 使用已有配置: {config.get('source_type')}")
        return _fetch_with_config(url, config, limit)

    # Step 2: 无配置，使用通用方式
    log(f"[获取] 无配置，使用 crawl4ai 通用方式")
    return _fetch_generic(url, limit)


def _get_source_config(url: str) -> dict | None:
    """获取数据源配置"""
    sources = list_sources_with_configs(include_inactive=False)
    src = next((s for s in sources if s.get("url_norm") == url or s.get("url") == url), None)
    if not src:
        return None

    list_config_str = src.get("list_config")
    if not list_config_str:
        return None

    list_config = parse_json_field(list_config_str)
    return {
        "source_name": src.get("name"),
        "source_type": src.get("source_type"),
        "list_config": list_config,
    }


def _fetch_with_config(url: str, config: dict, limit: int) -> dict:
    """使用 list_config 配置获取新闻"""
    source_type = config.get("source_type", "")
    list_config = config.get("list_config")
    source_name = config.get("source_name")

    # 根据 source_type 选择获取方式
    if source_type == "raw":
        news_items = _fetch_raw(url, config)
    else:
        # HTML/ajax/api 等统一走 HTML 采集流程
        news_items = _fetch_html_with_selector(url, config, limit)
        if not news_items:
            news_items = _fetch_generic(url, limit).get("news", [])

    return {
        "ok": True,
        "source_name": source_name,
        "source_type": source_type or "html",
        "count": len(news_items),
        "news": news_items[:limit],
    }

def _fetch_raw(url: str, config: dict) -> list:
    """使用 embedded JSON 配置获取新闻"""
    list_config = config.get("list_config")
    if not list_config:
        return []

    raw_html = fetch_raw_html(url)
    if not raw_html:
        return []

    json_data = find_embedded_json(raw_html)
    if not json_data:
        return []

    return extract_news_items(
        json_data,
        url_field=list_config.get("url_field", "url"),
        title_field=list_config.get("title_field", "title"),
        time_field=list_config.get("time_field", "createTime"),
        summary_field=list_config.get("summary_field", "summary"),
        date_format=list_config.get("date_format"),
    )


def _fetch_html_with_selector(url: str, config: dict, limit: int) -> list:
    """使用 CSS 选择器从 HTML 提取新闻"""
    list_config = config.get("list_config")
    if not list_config:
        return []

    # 构建选择器配置
    selector_cfg = _build_selector_cfg(list_config)
    if not selector_cfg:
        return []

    # 使用 crawl4ai 获取渲染 HTML
    _, html = asyncio.run(_fetch_html(url))
    if not html:
        return []

    return _extract_with_css_selectors(html, url, selector_cfg, limit)


def _build_selector_cfg(list_config: dict) -> dict:
    """从 list_config 构建选择器配置"""
    css_selector = list_config.get("css_selector") or list_config.get("item_selector")
    if not css_selector:
        container_tag = list_config.get("container_tag", "div")
        item_tag = list_config.get("item_tag", "a")
        css_selector = f"{container_tag} {item_tag}[href]"

    # 清理选择器转义
    def clean_sel(s):
        return s.replace(r'\-', '-').replace(r'\[', '[').replace(r'\]', ']') if s else s

    field_selectors = {}
    raw_fs = list_config.get("field_selectors", {})
    for k, v in raw_fs.items():
        field_selectors[k] = clean_sel(v) if isinstance(v, str) else v

    return {
        "item": clean_sel(css_selector),
        "title": list_config.get("item_tag", "a"),
        "url": f"{list_config.get('item_tag', 'a')}[href]",
        "field_selectors": field_selectors,
    }


def _extract_with_css_selectors(html: str, base_url: str, selector_cfg: dict, limit: int) -> list:
    """使用 CSS 选择器提取新闻"""
    item_sel = selector_cfg.get("item", "li")
    field_selectors = selector_cfg.get("field_selectors", {})
    title_sel = field_selectors.get("title_selector") or selector_cfg.get("title", "a")
    url_sel = field_selectors.get("url_selector") or selector_cfg.get("url", "a")
    date_sel = field_selectors.get("time_selector")
    summary_sel = field_selectors.get("summary_selector")

    soup = BeautifulSoup(html, 'html.parser')
    articles = []

    try:
        items = soup.select(item_sel)
    except Exception:
        return []

    for item in items[:limit]:
        # 提取日期
        date_str = None
        if date_sel:
            try:
                date_el = item.select_one(date_sel)
                if date_el:
                    date_str = date_el.get_text(strip=True)
                    from script.common.util import parse_publish_time
                    date_str = parse_publish_time(date_str)
            except Exception:
                pass

        # 提取标题和 URL
        title_el = None
        try:
            title_el = item.select_one(title_sel)
        except Exception:
            pass

        if not title_el and item.name == 'a':
            title_el = item

        if not title_el:
            continue

        raw_url = title_el.get("href", "") if hasattr(title_el, 'get') else ""
        if not raw_url and item.name == 'a':
            raw_url = item.get("href", "")

        # 相对路径转绝对路径
        if raw_url and not raw_url.startswith(('http://', 'https://', '//')):
            raw_url = urljoin(base_url, raw_url)

        title_text = title_el.get_text(separator='', strip=True)
        title_text = re.sub(r'\s+', ' ', title_text).strip()

        if len(title_text) <= 2:
            continue

        # 提取摘要
        summary = ""
        if summary_sel:
            try:
                summary_el = item.select_one(summary_sel)
                if summary_el:
                    summary = summary_el.get_text(separator=' ', strip=True)[:300]
            except Exception:
                pass

        articles.append({
            "title": title_text,
            "url": raw_url,
            "publish_time": date_str or "",
            "summary": summary,
        })

    return articles


def _fetch_generic(url: str, limit: int) -> dict:
    """通用方式获取新闻（无配置时使用）"""
    _, html = asyncio.run(_fetch_html(url))
    if not html:
        return {
            "ok": False,
            "source_type": "unknown",
            "count": 0,
            "news": [],
            "error": "无法获取页面内容",
        }

    articles = extract_article_links(html, url, html=html)
    if not articles:
        return {
            "ok": True,
            "source_type": "html",
            "count": 0,
            "news": [],
        }

    news_items = []
    for art in articles[:limit]:
        news_items.append({
            "title": art.get("title", ""),
            "url": art.get("url", ""),
            "publish_time": art.get("publish_time", ""),
            "summary": art.get("summary", ""),
        })

    return {
        "ok": True,
        "source_name": url,
        "source_type": "html",
        "count": len(news_items),
        "news": news_items,
    }