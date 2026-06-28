"""
source_learning.py - 数据源提取模式学习

委托给 discovery 模块实现：
  - list_discovery    - 列表页配置发现
  - content_discovery - 正文配置发现

抓取统一走 fetch_list_html / fetch_article_html 入口。
"""

import asyncio

try:
    from script.discovery.util.html_fetch import fetch_list_html, fetch_article_html
except ImportError:
    fetch_list_html = None
    fetch_article_html = None


async def learn_pattern_for_source(source_name: str, list_url: str, log_fn=print):
    """学习单个数据源的提取模式（委托给 discovery 模块）"""
    if fetch_list_html is None or fetch_article_html is None:
        log_fn("[ERROR] 缺少依赖: pip install crawl4ai")
        return None

    from script.discovery import (
        discover_list_config,
        discover_content_config,
        extract_article_links,
    )

    log_fn(f"\n{'=' * 60}")
    log_fn(f"学习数据源：{source_name}")
    log_fn(f"列表页URL：{list_url}")

    # 1. 抓取列表页（统一走 fetch_list_html 入口，覆盖 JS 动态渲染）
    try:
        _, html, markdown = await fetch_list_html(list_url, return_markdown=True)
    except Exception as e:
        log_fn(f"  [FAIL] 列表页异常：{e}")
        return None

    if not html:
        log_fn(f"  [FAIL] 列表页抓取失败")
        return None

    # 2. 列表配置发现
    list_config = discover_list_config(list_url, html)
    log_fn(f"  list_config: {list_config.get('source_type', 'N/A')}")

    # 3. 提取文章链接
    articles = extract_article_links(markdown or "", source_name, html=html)
    log_fn(f"  找到 {len(articles)} 个文章链接")

    if not articles:
        log_fn(f"  [WARN] 该数据源没有找到文章链接")
        return None

    # 4. 正文配置发现（只取第一篇）
    article_url = articles[0]["url"]
    log_fn(f"  使用文章页进行 content_discovery: {article_url}")

    try:
        _, article_html, _ = await fetch_article_html(article_url, return_markdown=True)
    except Exception as e:
        log_fn(f"  [FAIL] 文章页异常：{e}")
        return None

    if not article_html:
        log_fn(f"  [FAIL] 文章页抓取失败")
        return None

    content_config = discover_content_config(article_url, article_html)
    log_fn(f"  content_config: {content_config.get('content_extract', {}).get('selector', 'N/A')}")

    log_fn(f"\n{'=' * 60}")
    log_fn(f"学习完成：{source_name}")

    return {
        "source_type": list_config.get("source_type"),
        "list_config": list_config.get("list_config"),
        "publish_time_pattern": list_config.get("publish_time_pattern"),
        "contentExtract": content_config.get("content_extract"),
        "publishTimeExtract": content_config.get("publish_time_pattern"),
    }


async def learn_all_sources(sources: list, log_fn=print):
    """学习所有数据源"""
    log_fn(f"\n{'=' * 60}")
    log_fn(f"开始学习所有 {len(sources)} 个数据源")

    for i, source in enumerate(sources, 1):
        log_fn(f"\n[{i}/{len(sources)}] 处理数据源：{source['name']}")
        await learn_pattern_for_source(source["name"], source["url"], log_fn)
        await asyncio.sleep(2)

    log_fn(f"\n{'=' * 60}")
    log_fn("全部学习完成")
