"""
list_crawler CLI - 列表采集命令行入口

支持三种模式：
- 无参数：全量采集所有数据源
- 单 URL：测试单个数据源（python list_crawler.py <url>）
- --learn <url>：进入学习模式（python list_crawler.py --learn <url> [...]）
"""
from __future__ import annotations

import asyncio
import sys
from datetime import date

# -*- 在 import bootstrap 前解析 --db 参数 -*-
import os
import sys
for i, arg in enumerate(sys.argv):
    if arg == "--db" and i + 1 < len(sys.argv):
        os.environ["NEWS_DB"] = sys.argv[i + 1]
        break

from script.bootstrap import *
from script.crawl.crawl_config import get_crawl_config
from script.crawl.crawl_db import start_batch, get_all_urls
from script.crawl.list_crawler import crawl_raw_source
from script.crawl.news_list.html_list import crawl_html_source
from script.db.sources_db import list_sources_with_configs, normalize_url


def _parse_learn_args(argv: list) -> tuple[str, str, str, bool, bool]:
    """解析 --learn 模式的参数"""
    if len(argv) < 3:
        print("用法: python list_crawler.py --learn <url> [--title \"标题\"] [--name \"名称\"] [--skip-article] [--force-relearn]")
        sys.exit(1)
    target_url = argv[2]

    headline = ""
    source_name = ""
    skip_article_crawler = False
    force_relearn = False

    if "--title" in argv:
        idx = argv.index("--title")
        if idx + 1 < len(argv):
            headline = argv[idx + 1]
    if "--name" in argv:
        idx = argv.index("--name")
        if idx + 1 < len(argv):
            source_name = argv[idx + 1]
    if "--skip-article" in argv:
        skip_article_crawler = True
    if "--force-relearn" in argv:
        force_relearn = True

    return target_url, source_name, headline, skip_article_crawler, force_relearn


def _run_learn_mode(argv: list) -> None:
    """--learn 模式：调用 learn_source_config"""
    import json
    from script.discovery import learn_source_config

    target_url, source_name, headline, skip_article_crawler, force_relearn = _parse_learn_args(argv)

    print(f"开始学习: {target_url}")
    if headline:
        print(f"  附加标题: {headline}")
    if source_name:
        print(f"  数据源名称: {source_name}")
    if skip_article_crawler:
        print(f"  跳过正文抓取: True")
    if force_relearn:
        print(f"  强制重新学习: True")

    result = learn_source_config(
        url=target_url,
        name=source_name or target_url,
        headline=headline,
        skip_article_crawler=skip_article_crawler,
        force_relearn=force_relearn,
    )
    if not result:
        print("学习失败，返回空配置")
        sys.exit(1)

    print("\n学习完成:")
    print(f"  发现方法: {result.get('discovery_method', 'unknown')}")
    print(f"  source_type: {result.get('source_type')}")
    print(f"  list_complete: {result.get('list_complete')}")
    print(f"  article_url: {result.get('article_url')}")
    lc = result.get("list_config", {})
    ce = result.get("content_extract")
    print(f"  list_config: {json.dumps(lc, ensure_ascii=False)[:300]}...")
    if ce:
        print(f"  content_extract: {json.dumps(ce, ensure_ascii=False)[:200]}...")


def _run_single_source_mode(target_url: str) -> None:
    """单源测试模式：python list_crawler.py <url>"""
    cfg = get_crawl_config()
    global_limit = cfg["crawNumPerSource"]
    global_max_consecutive = cfg.get("maxConsecutiveNonToday", 3)

    sources = list_sources_with_configs(include_inactive=False)
    target_norm = normalize_url(target_url)
    source = next((s for s in sources if s.get("url_norm") == target_norm or s.get("url") == target_url), None)
    if not source:
        print(f"未找到数据源: {target_url}")
        sys.exit(1)
    print(f"测试数据源: {source['name']} ({target_url})")
    print(f"数据源类型: {source.get('source_type', 'unknown')}")
    batch_id = start_batch()
    today = date.today()
    existing_urls = get_all_urls()

    source_type = source.get("source_type", "")
    if source_type == "raw":
        result = asyncio.run(crawl_raw_source(source, batch_id, today, existing_urls))
        print(f"结果: 当天入库 {result.get('today', 0)}, 非当天 {result.get('old', 0)}")
    else:
        result = asyncio.run(crawl_html_source(source, batch_id, global_limit, global_max_consecutive, existing_urls))
        if result:
            print(f"结果: 当天入库 {result['today']}, 非当天 {result['old']}")
        else:
            print("结果: 无新文章入库")


def main() -> None:
    """CLI 入口分发"""
    from script.crawl.list_crawler import main as run_bulk_crawl

    if len(sys.argv) > 1:
        target = sys.argv[1]
        if target == "--learn":
            _run_learn_mode(sys.argv)
        else:
            _run_single_source_mode(target)
    else:
        asyncio.run(run_bulk_crawl())


if __name__ == "__main__":
    main()