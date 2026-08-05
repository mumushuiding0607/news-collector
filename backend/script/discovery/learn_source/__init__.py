"""
learn_source - 统一的学习接口

同时完成列表发现和正文发现，保留已有有效配置，保存到 source_crawl_configs 表。

执行流程：
    Step 0: 加载已有配置
    Step 1.1: crawl4ai 抓取列表页
    Step 1.2/2: 列表发现（含保留/覆盖策略）
    Step 2.1: skip_article_crawler 时设置 list_complete
    Step 3: 提取样本文章 URL
    Step 4: 正文发现（含保留/覆盖策略）
    Step 5: 保存到数据库
"""
from __future__ import annotations

from ._article import extract_sample_article
from ._content import discover_content_with_policy
from ._existing import load_existing_config
from ._list import apply_list_complete, discover_list_with_policy, fetch_list_html
from ._save import build_result, save_learned_config
from script.discovery.html_cleaner import clean_html
from script.discovery.util.news_block_truncator import truncate_html_by_news_items

__all__ = ["learn_source_config"]


def learn_source_config(
    url: str,
    name: str,
    headline: str = "",
    skip_article_crawler: bool = False,
    force_relearn: bool = False,
) -> dict:
    """
    统一的学习接口：同时完成列表发现和正文发现。

    Args:
        url: 数据源 URL（必填）
        name: 数据源名称（必填）
        headline: 已知标题（可选，用于多候选列表时消歧）
        skip_article_crawler: 是否跳过 article_crawler（True 时设置 list_complete=True）
        force_relearn: 是否强制重新学习（默认 False 保留已有配置）

    Returns:
        配置字典，包含 list_config 和 content_extract
    """
    from script.discovery.list_discovery import log
    from script.db import init_db
    init_db()  # 确保数据库表已创建
    log(f"[统一学习] 开始学习: {name} ({url})")
    if headline:
        log(f"[统一学习] 附加标题: {headline}")

    # Step 0
    existing_list_config, existing_content_extract = load_existing_config(url)

    # Step 1.1
    list_html = fetch_list_html(url)
    if not list_html:
        return {}

    # Step 1.1.5: 与 test_learn_flow.py 对齐，先清洗再截断
    cleaned = clean_html(list_html)
    cleaned_html = cleaned.html
    log(f"[统一学习] HTML 清洗完成，移除 {cleaned.removed_count} 个标签")
    truncated_html = truncate_html_by_news_items(cleaned_html, max_size=200*1024)
    log(f"[统一学习] HTML 截断后长度: {len(truncated_html)}")

    # Step 1.2/2
    list_config, saved_source_type, discovery_method = discover_list_with_policy(
        url, truncated_html, existing_list_config, headline, force_relearn,
    )

    # Step 2.1
    list_config = apply_list_complete(list_config, skip_article_crawler)

    # Step 3
    article_url, article_title, sample_news = extract_sample_article(
        list_config, truncated_html, name, base_url=url,
    )

    # Step 4
    content_config = discover_content_with_policy(
        article_url, existing_content_extract, skip_article_crawler, force_relearn, url,
        article_title,
    )

    # Step 5
    if not save_learned_config(url, name, list_config, content_config):
        return {}

    return build_result(
        name=name, url=url, list_config=list_config, content_config=content_config,
        saved_source_type=saved_source_type, discovery_method=discovery_method,
        article_url=article_url, article_title=article_title,
        sample_news=sample_news, skip_article_crawler=skip_article_crawler,
    )