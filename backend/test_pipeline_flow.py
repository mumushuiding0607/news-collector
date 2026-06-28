#!/usr/bin/env python
"""
test_pipeline_flow.py - 基于已学习配置，对单 URL 执行实际采集

使用 list_crawler 和 article_crawler 的现有逻辑，对已学习的 URL 进行实际抓取，
验证 list_dom_result 和 content_config 配置是否正确。

用法：
    cd backend
    python test_pipeline_flow.py <url> [--list-only] [--article-only]

示例：
    python test_pipeline_flow.py http://news.smm.cn/live
    python test_pipeline_flow.py http://tv.cctv.com/lm/dysj --list-only
    python test_pipeline_flow.py http://www.cnenergynews.cn/ --article-only
"""
import argparse
import asyncio
import json
import sys
from datetime import date
from pathlib import Path

# 添加 backend 到 path
sys.path.insert(0, str(Path(__file__).parent))


def get_output_name(url: str) -> str:
    """从 URL 提取输出文件名（与 test_learn_flow.py 一致）"""
    from urllib.parse import urlparse
    parsed = urlparse(url)
    path = parsed.path.strip("/").replace("/", "_")
    return f"{parsed.netloc.replace('.', '_')}_{path}" if path else parsed.netloc.replace('.', '_')


def load_learning_result(name: str) -> tuple[dict | None, dict | None]:
    """
    从 test/list_dom_result/ 和 test/content_config/ 加载已学习的配置。

    Returns:
        (list_config, content_config) 两个 dict 或 None
    """
    test_dir = Path(__file__).parent.parent / "test"
    list_dom_path = test_dir / "list_dom_result" / f"{name}.json"
    content_path = test_dir / "content_config" / f"{name}.json"

    list_config = None
    if list_dom_path.exists():
        with open(list_dom_path, "r", encoding="utf-8") as f:
            list_config = json.load(f)

    content_config = None
    if content_path.exists():
        with open(content_path, "r", encoding="utf-8") as f:
            content_config = json.load(f)

    return list_config, content_config


def save_to_db(url: str, list_config: dict | None, content_config: dict | None) -> bool:
    """
    将学习结果写入 DB（source_crawl_configs 表）。
    """
    from script.db.sources_db import upsert_crawl_config

    if not list_config:
        print("[ERROR] list_config 为空，无法写入 DB")
        return False

    name = list_config.get("name", url)

    lc = list_config.get("list_config", {})
    ce = content_config.get("content_extract", {}) if content_config else None
    pt = content_config.get("publish_time_pattern", "") if content_config else ""

    upsert_crawl_config(
        url=url,
        name=name,
        source_type=list_config.get("source_type", "html"),
        list_config=lc,
        content_extract=json.dumps(ce, ensure_ascii=False) if ce else None,
        publish_time_pattern=pt,
    )
    print(f"[DB] 写入完成")
    return True


async def run_list_crawler(url: str, limit: int = 50) -> dict:
    """
    执行列表采集（复用 html_list.crawl_html_source 逻辑）。
    """
    from script.db.sources_db import list_sources_with_configs, normalize_url
    from script.crawl.crawl_db import start_batch, get_all_urls
    from script.crawl.news_list.html_list import crawl_html_source

    sources = list_sources_with_configs(include_inactive=False)
    target_norm = normalize_url(url)
    source = next(
        (s for s in sources if s.get("url_norm") == target_norm or s.get("url") == url),
        None,
    )
    if not source:
        return {"error": f"DB 中未找到数据源: {url}"}

    batch_id = start_batch()
    today = date.today()
    existing_urls = get_all_urls()

    if source.get("source_type") == "raw":
        from script.crawl.list_crawler import crawl_raw_source
        result = await crawl_raw_source(source, batch_id, today, existing_urls)
    else:
        result = await crawl_html_source(
            source,
            batch_id,
            limit,
            3,  # maxConsecutiveNonToday
            existing_urls,
        )
    return result


async def run_article_crawler(limit: int = 20) -> dict:
    """
    执行文章正文采集（复用 article_crawler 逻辑）。
    """
    from script.db.primary_source import get_useful_uncrawled, mark_article_crawled
    from script.crawl.article_crawler import _crawl_one_article
    from script.db import get_conn

    rows = get_useful_uncrawled(limit=limit)
    if not rows:
        return {"crawled": 0, "skipped": 0}

    success = 0
    for row in rows:
        try:
            await _crawl_one_article(row)
            mark_article_crawled(row["id"])
            success += 1
        except Exception as e:
            print(f"[WARN] 采集失败: {row.get('url', '')}: {e}")

    return {"crawled": success, "total": len(rows)}


def main():
    parser = argparse.ArgumentParser(description="基于学习配置的采集测试")
    parser.add_argument("url", help="数据源 URL")
    parser.add_argument("--list-only", action="store_true", help="仅采集列表")
    parser.add_argument("--article-only", action="store_true", help="仅采集正文")
    parser.add_argument("--limit", type=int, default=50, help="每源采集上限")
    parser.add_argument("--save-db", action="store_true", help="仅写入 DB 配置，不采集")
    args = parser.parse_args()

    url = args.url
    name = get_output_name(url)
    print(f"[INFO] URL: {url}")
    print(f"[INFO] Name: {name}")

    # 加载学习结果
    list_config, content_config = load_learning_result(name)
    if not list_config:
        print(f"[ERROR] 未找到 list_dom_result: test/list_dom_result/{name}.json")
        sys.exit(1)

    # 写入 DB
    if not save_to_db(url, list_config, content_config):
        sys.exit(1)

    if args.save_db:
        print("[DONE] 配置已写入 DB，退出（--save-db 模式）")
        sys.exit(0)

    # 执行采集
    if args.list_only:
        print(f"\n[采集列表] {url}")
        result = asyncio.run(run_list_crawler(url, limit=args.limit))
        print(f"[结果] {result}")
    elif args.article_only:
        print(f"\n[采集正文] （最近 {args.limit} 条未采文的文章）")
        result = asyncio.run(run_article_crawler(limit=args.limit))
        print(f"[结果] {result}")
    else:
        print(f"\n[采集列表] {url}")
        result1 = asyncio.run(run_list_crawler(url, limit=args.limit))
        print(f"[列表结果] {result1}")
        print(f"\n[采集正文] （最近 {args.limit} 条未采文的文章）")
        result2 = asyncio.run(run_article_crawler(limit=args.limit))
        print(f"[正文结果] {result2}")


if __name__ == "__main__":
    main()
