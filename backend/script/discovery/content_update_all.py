"""
content_update_all.py - 批量更新所有数据源的正文配置

针对 content_extract 为空的数据源，并行抓取列表页 HTML 并发现正文配置。
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

from script.bootstrap import *
from script.db.sources_db import list_sources_with_configs, upsert_crawl_config
from script.discovery.content_discovery import discover_content_config, log
from script.discovery.util.html_fetch import fetch_list_html as _fetch_html


async def _process_sources() -> dict:
    """批量更新正文配置"""
    log("=" * 60)
    log("开始批量更新正文配置")
    log("=" * 60)

    sources = list_sources_with_configs(include_inactive=False)
    sources = [s for s in sources if s.get("config_id") is not None]

    # 先批量抓取所有 HTML
    url_source_map = {}
    for source in sources:
        url = source["url"] or source.get("config_url", "")
        if url:
            url_source_map[url] = source

    # 并行抓取 HTML
    html_results = {}
    if url_source_map:
        tasks = [_fetch_html(url) for url in url_source_map]
        results = await asyncio.gather(*tasks)
        for url, html in results:
            html_results[url] = html

    success_count = 0
    failed_count = 0
    skipped_count = 0

    for source in sources:
        source_id = source["id"]
        name = source["name"]
        url = source["url"] or source.get("config_url", "")

        if not url:
            log(f"[跳过] id={source_id}, name={name}, url为空")
            failed_count += 1
            continue

        existing_content_extract = source.get("content_extract")
        if existing_content_extract:
            log(f"[跳过] id={source_id}, name={name}, 已有有效配置")
            skipped_count += 1
            continue

        html = html_results.get(url, "")
        if not html:
            log(f"  [失败] 无法获取 HTML")
            failed_count += 1
            continue

        log(f"\n处理: {name} ({url})")

        try:
            config = discover_content_config(url, html)
            if not config:
                log("  [失败] LLM 返回空配置")
                failed_count += 1
                continue

            ce = config.get("content_extract")
            upsert_crawl_config(
                url=url,
                content_extract=json.dumps(ce) if ce else None,
                publish_time_pattern=config.get("publish_time_pattern"),
            )

            log(f"  [成功] content_extract={config.get('content_extract', {}).get('selector', 'N/A')}")
            success_count += 1

        except Exception as e:
            log(f"  [失败] {e}")
            failed_count += 1

    log("\n" + "=" * 60)
    log(f"更新完成: 成功 {success_count}, 失败 {failed_count}, 跳过 {skipped_count}, 总计 {len(sources)}")
    log("=" * 60)

    return {"success": success_count, "failed": failed_count, "skipped": skipped_count, "total": len(sources)}


def update_all_configs() -> dict:
    """批量更新所有数据源的正文配置（使用新事件循环运行异步任务）"""
    return asyncio.run(_process_sources())


if __name__ == "__main__":
    """单独运行 content_update_all，只针对 content_extract 为空的数据源"""
    result = update_all_configs()
    print(f"\n完成: 成功 {result['success']}, 失败 {result['failed']}, 跳过 {result['skipped']}")