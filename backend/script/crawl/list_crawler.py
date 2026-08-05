"""
list_crawler.py - Step 1: 采集列表页

只从列表页提取标题、发布日期、摘要，content 留空。
不访问文章链接（那是 Step 3 的职责）。

每次执行生成新的 batch_id，crawNumPerSource 控制每源入库数量。

数据源拆分：
- Raw 类型：原始 HTTP 获取，解析嵌入式 JSON
- 其他类型（HTML/ajax/api 等）：统一走 HTML 采集流程
"""
import asyncio
import json
import sys
from datetime import date

# 在 import bootstrap 前解析 --type 参数（必须最早执行）
from script.bootstrap import parse_db_arg
sys.argv = parse_db_arg(sys.argv)

from crawl4ai import AsyncWebCrawler, BrowserConfig

from script.bootstrap import *
from script.crawl.crawl_config import get_crawl_config
from script.crawl.crawl_db import start_batch, get_all_urls
from script.crawl.news_list.html_list import crawl_html_source
from script.db.sources_db import list_sources_with_configs
from script.log import log as _log
from script.common.datetimeutil import now_iso


def log(msg: str):
    _log("list_crawler", msg)


# 跨源并发上限：从 config 读取，避免一次开太多浏览器 tab 导致内存炸/反爬警觉


today = date.today()
today_str = today.strftime("%Y-%m-%d")


async def main():
    log("=" * 60)
    log(f"Step 1 [List Crawl] start {now_iso()}")
    log(f"Target date: {today_str}")

    cfg = get_crawl_config()
    global_limit = cfg["crawNumPerSource"]
    global_max_consecutive = cfg["maxConsecutiveNonToday"]
    max_source_concurrency = cfg.get("maxSourceConcurrency", 5)

    db_sources = list_sources_with_configs(include_inactive=False)
    sources = [s for s in db_sources if s.get("config_id") is not None and s.get("checked") == 1]
    log(f"Sources loaded from DB: {len(sources)} (checked=1), crawNumPerSource={global_limit}, maxConsecutiveNonToday={global_max_consecutive}")

    # 按 source_type 分离
    raw_sources = [s for s in sources if s.get("source_type") == "raw"]
    api_sources = [s for s in sources if s.get("source_type") == "api"]
    other_sources = [s for s in sources if s.get("source_type") not in ("raw", "api")]
    log(f"Raw 数据源: {len(raw_sources)}, API 数据源: {len(api_sources)}, "
        f"其他数据源: {len(other_sources)} (并发上限 {max_source_concurrency})")

    batch_id = start_batch()
    existing_urls = get_all_urls()
    log(f"已入库URL: {len(existing_urls)} 个")

    # Raw 类型数据源（纯 HTTP，无 Chromium 开销，串行即可）
    raw_results = []
    for source in raw_sources:
        result = await crawl_raw_source(source, batch_id, today, existing_urls)
        if result:
            raw_results.append(result)

    # API 类型数据源（纯 HTTP 调用 list_config.endpoint，串行即可）
    api_results = []
    for source in api_sources:
        result = await _crawl_api_source(source, batch_id, today)
        if result:
            api_results.append(result)

    # 跨源 asyncio.gather 并发，并用 Semaphore 限制同时活跃的 tab 数
    other_results: list[dict] = []
    if other_sources:
        sem = asyncio.Semaphore(max_source_concurrency)

        async def _crawl_one(source, crawler):
            async with sem:
                return await crawl_html_source(
                    source, batch_id, global_limit, global_max_consecutive,
                    existing_urls, cfg, crawler=crawler,
                )

        async with AsyncWebCrawler(config=BrowserConfig(headless=True)) as crawler:
            results = await asyncio.gather(
                *[_crawl_one(s, crawler) for s in other_sources],
                return_exceptions=True,
            )
        for s, r in zip(other_sources, results):
            if isinstance(r, Exception):
                log(f"  [EXC] {s.get('name')}: {r}")
                continue
            if r:
                other_results.append(r)

    # 汇总统计
    total_today = sum(r.get("today", 0) for r in raw_results + api_results + other_results)
    total_old = sum(r.get("old", 0) for r in raw_results + api_results + other_results)
    total_no_date = sum(r.get("no_date", 0) for r in other_results)
    no_date_sources: dict[str, int] = {}
    for r in other_results:
        for k, v in r.get("no_date_sources", {}).items():
            no_date_sources[k] = no_date_sources.get(k, 0) + v

    log("\n" + "=" * 60)
    log("采集完成")
    log(f"当天有效入库: {total_today}")
    log(f"非当天丢弃: {total_old}")
    log(f"无法确认日期: {total_no_date}")

    if no_date_sources:
        log("\n无法确认日期的信源（请人工确认日期格式）：")
        for sn, cnt in no_date_sources.items():
            log(f"  - {sn}: {cnt} 篇")


async def crawl_raw_source(source: dict, batch_id: int, target_date, existing_urls: set) -> dict:
    """采集 Raw 类型数据源（原始 HTTP 获取，解析嵌入式 JSON）"""
    from script.db.primary_source import batch_insert
    from script.discovery.raw_fetch import fetch_raw_html
    from script.discovery.embedded_json import find_embedded_json, extract_news_items
    from script.common.jsonutil import parse_json_field

    name = source["name"]
    list_url = source.get("url_norm") or source.get("url", "")

    log(f"\n-> Raw [List] {name}: {list_url}")

    # 使用 raw_fetch 获取 HTML
    raw_html = fetch_raw_html(list_url)
    if not raw_html:
        log(f"  [FAIL] raw fetch 失败")
        return {"today": 0, "old": 0}

    # 解析嵌入式 JSON
    json_data = find_embedded_json(raw_html)
    if not json_data:
        log(f"  [FAIL] 未检测到嵌入式 JSON")
        return {"today": 0, "old": 0}

    # 获取字段映射
    list_config_str = source.get("list_config")
    list_config = parse_json_field(list_config_str) if list_config_str else {}

    # 提取新闻条目（使用学习的字段映射）
    news_items = extract_news_items(
        json_data,
        url_field=list_config.get("url_field", "url"),
        title_field=list_config.get("title_field", "title"),
        time_field=list_config.get("time_field", "createTime"),
        summary_field=list_config.get("summary_field", "summary"),
        date_format=list_config.get("date_format"),
    )
    if not news_items:
        log(f"  [FAIL] 解析到 0 条新闻")
        return {"today": 0, "old": 0}

    log(f"  解析到 {len(news_items)} 条新闻")

    # 过滤当天数据
    today_str = target_date.strftime("%Y-%m-%d")
    today_items = [
        item for item in news_items
        if item.get("time", "").startswith(today_str)
    ]
    log(f"  当天 {len(today_items)} 条")

    # 入库
    if today_items:
        articles = [
            {
                "source_name": name,
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "summary": item.get("summary", ""),
                "publish_time": item.get("time", ""),
                "content": "",
                "content_length": 0,
                "batch_id": batch_id,
            }
            for item in today_items
        ]
        success_count = batch_insert(articles, batch_id)
        log(f"  入库 {success_count}/{len(today_items)} 条")
        return {"today": success_count, "old": 0}
    else:
        return {"today": 0, "old": 0}


async def _crawl_api_source(source: dict, batch_id: int, target_date) -> dict:
    """采集 API 类型数据源（调用 list_config.endpoint，直接入库）

    复用 crawl_api_source（api_list.py）做调用 + 入库，返回统一统计格式。
    """
    from script.crawl.news_list.api_list import crawl_api_source

    name = source.get("name", "未知数据源")
    log(f"\n-> API [List] {name}")

    # crawl_api_source 是同步函数，会自己处理入库
    # 注意：crawl_api_source 内部会过滤当天数据并入库，返回 {today: N, total: M}
    result = crawl_api_source(source, batch_id, target_date)
    today = result.get("today", 0) or 0
    total = result.get("total", 0) or 0
    log(f"  API 完成: today={today}, total={total}")
    return {"today": today, "old": max(0, total - today)}


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--learn":
        # --learn 模式：python -m script.crawl.list_crawler --learn <url> [--type T] [--title T] [--name N] [--skip-article] [--force-relearn]
        from script.discovery import learn_source_config
        from script.common.urlutil import normalize_url

        if len(sys.argv) < 3:
            print("用法: python -m script.crawl.list_crawler --learn <url> "
                  "[--type 股市新闻|AI新闻] [--title \"标题\"] [--name \"名称\"] [--skip-article] [--force-relearn]")
            sys.exit(1)

        target_url = sys.argv[2]
        headline = ""
        source_name = ""
        skip_article_crawler = False
        force_relearn = False
        args = sys.argv[3:]

        i = 0
        while i < len(args):
            a = args[i]
            if a == "--title" and i + 1 < len(args):
                headline = args[i + 1]; i += 2
            elif a == "--name" and i + 1 < len(args):
                source_name = args[i + 1]; i += 2
            elif a == "--skip-article":
                skip_article_crawler = True; i += 1
            elif a == "--force-relearn":
                force_relearn = True; i += 1
            else:
                print(f"未知参数: {a}"); sys.exit(1)

        if not source_name:
            source_name = normalize_url(target_url)

        print(f"开始学习: {target_url}")
        if headline:                print(f"  附加标题: {headline}")
        if source_name:             print(f"  数据源名称: {source_name}")
        if skip_article_crawler:    print(f"  跳过正文抓取: True")
        if force_relearn:           print(f"  强制重新学习: True")

        result = learn_source_config(
            url=target_url,
            name=source_name,
            headline=headline,
            skip_article_crawler=skip_article_crawler,
            force_relearn=force_relearn,
        )
        if not result:
            print("学习失败，返回空配置")
            sys.exit(1)

        print(f"\n学习完成:")
        print(f"  发现方法: {result.get('discovery_method', 'unknown')}")
        print(f"  source_type: {result.get('source_type')}")
        print(f"  list_complete: {result.get('list_complete')}")
        print(f"  article_url: {result.get('article_url')}")
        lc = result.get("list_config", {})
        ce = result.get("content_extract")
        print(f"  list_config: {json.dumps(lc, ensure_ascii=False)[:300]}")
        if ce:
            print(f"  content_extract: {json.dumps(ce, ensure_ascii=False)[:300]}")
    elif len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
        # 单源测试模式：python -m script.crawl.list_crawler <url>
        from script.common.urlutil import normalize_url

        target_url = sys.argv[1]
        target_norm = normalize_url(target_url)
        sources = list_sources_with_configs(include_inactive=False)
        source = next(
            (s for s in sources if s.get("url_norm") == target_norm or s.get("url") == target_url),
            None,
        )
        if not source:
            print(f"未找到数据源: {target_url}")
            sys.exit(1)
        print(f"测试数据源: {source['name']} ({target_url})")
        print(f"数据源类型: {source.get('source_type', 'unknown')}")

        cfg = get_crawl_config()
        global_limit = cfg["crawNumPerSource"]
        global_max_consecutive = cfg.get("maxConsecutiveNonToday", 10)
        batch_id = start_batch()
        existing_urls = get_all_urls()
        source_type = source.get("source_type", "")

        if source_type == "raw":
            result = asyncio.run(crawl_raw_source(source, batch_id, today, existing_urls))
            print(f"结果: 当天入库 {result.get('today', 0)}, 非当天 {result.get('old', 0)}")
        else:
            result = asyncio.run(crawl_html_source(
                source, batch_id, global_limit, global_max_consecutive, existing_urls, cfg,
            ))
            if result:
                print(f"结果: 当天入库 {result.get('today', 0)}, 非当天 {result.get('old', 0)}, "
                      f"无法确认日期 {result.get('no_date', 0)}, 已采 {result.get('processed', 0)}")
            else:
                print("结果: 无新文章入库")
    else:
        asyncio.run(main())