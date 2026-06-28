"""
find_stocks_logic.py - 事件驱动的核心标的发现（业务逻辑）

从 importance 表读取高分积极新闻，逐条调用 LLM 生成关联核心标的，
结果存入 news_stocks 表。
"""

import asyncio
import time
from pathlib import Path

from script.bootstrap import *
from script.db import (
    get_conn, put_conn,
    insert_news_stocks, get_processed_importance_ids,
    get_max_batch_id,
)
from script.crawl.crawl_config import get_crawl_config
from script.llm import call_async_raw
from script.log import log as _log, init_log
from script.common.datetimeutil import now_iso


PROMPT_FILE = Path(__file__).resolve().parent.parent.parent / "prompt" / "核心标的.md"
_TEMPLATE_CACHE: str | None = None
BATCH_SIZE = 3  # 每批处理多少条新闻


def log(msg: str):
    _log("find_stocks", msg)


def _get_template() -> str:
    global _TEMPLATE_CACHE
    if _TEMPLATE_CACHE is None:
        _TEMPLATE_CACHE = PROMPT_FILE.read_text(encoding="utf-8")
    return _TEMPLATE_CACHE


def parse_stocks_from_json(text: str) -> list[dict]:
    """从 LLM 输出解析 JSON 数组"""
    import json
    import re

    # 提取 JSON 数组
    m = re.search(r'\[[\s\S]*\]', text)
    if not m:
        return []
    try:
        data = json.loads(m.group())
        if not isinstance(data, list):
            return []
        stocks = []
        for item in data:
            if not isinstance(item, dict) or 'name' not in item:
                continue
            stock = {
                'code': item.get('code', ''),
                'name': item['name'],
                'tier': item.get('tier', ''),
                'chain_link': item.get('chain_link', ''),
                'four_dims': item.get('four_dims', {}),
                'moat': item.get('moat', ''),
                'news_related': item.get('news_related', ''),
            }
            if 'news_index' in item:
                stock['news_index'] = item['news_index']
            stocks.append(stock)
        return stocks
    except (json.JSONDecodeError, KeyError):
        return []


def build_prompt(news_title: str, news_summary: str) -> str:
    """构建单条新闻的提示词"""
    template = _get_template()
    parts = []
    if news_title:
        parts.append(f"标题：{news_title}")
    if news_summary:
        parts.append(f"摘要：{news_summary}")
    news_content = "\n".join(parts)
    return template.replace("<<news_content>>", news_content)


def build_batch_prompt(news_list: list[dict]) -> str:
    """构建批量新闻的提示词"""
    template = _get_template()
    blocks = []
    for i, news in enumerate(news_list):
        parts = []
        if news.get("title"):
            parts.append(f"标题：{news['title']}")
        if news.get("summary"):
            parts.append(f"摘要：{news['summary']}")
        blocks.append(f"--- 新闻{i} ---\n" + "\n".join(parts))
    news_content = "\n\n".join(blocks)
    return template.replace("<<news_content>>", news_content)


def findStocks(dry_run: bool = False, min_score: int = 6) -> dict:
    """
    从 importance 表读取高分积极新闻，调用 LLM 生成关联核心标的。

    内部用单一 event loop 串行调用 LLM（约束：LLM 必须串行）。
    相比每条新建 event loop 的反模式，aiohttp 连接池可复用。
    """
    init_log()
    log("=" * 60)
    log(f"findStocks start {now_iso()}")
    log(f"Mode: {'DRY-RUN' if dry_run else 'LIVE'},最低评分: {min_score}")
    log("=" * 60)

    return asyncio.run(_run_find_stocks(dry_run=dry_run, min_score=min_score))


async def _run_find_stocks(dry_run: bool, min_score: int) -> dict:
    max_batch = get_max_batch_id()
    if not max_batch:
        log("无最新批次，退出")
        return {"total": 0, "processed": 0, "stocks_found": 0}

    conn = get_conn()
    cur = conn.execute("""
        SELECT id, news_id, source_name, title, url, publish_time,
               summary, related_sectors, importance_score, reason,
               direction, intensity, expected_change, duration,
               expectation_level, market_mode, created_at
        FROM importance
        WHERE batch_id = ?
          AND importance_score >= ?
          AND direction = '积极'
          AND date(publish_time, 'localtime') = date('now', 'localtime')
        ORDER BY importance_score DESC
    """, (max_batch, min_score))
    rows = cur.fetchall()
    put_conn(conn)

    if not rows:
        log(f"无评分>{min_score} 且方向积极 且 发布日期为今天的新闻")
        return {"total": 0, "processed": 0, "stocks_found": 0}

    log(f"待处理新闻: {len(rows)} 条（仅当天）")
    processed = get_processed_importance_ids()
    log(f"已处理: {len(processed)} 条")

    # 按 batch 分组
    batches: list[list[tuple]] = []
    for row in rows:
        if row[0] in processed:
            log(f"  -> id={row[0]} 已处理，跳过")
            continue
    remaining = [row for row in rows if row[0] not in processed]
    for i in range(0, len(remaining), BATCH_SIZE):
        batches.append(remaining[i:i + BATCH_SIZE])

    log(f"分批: {len(batches)} 批（每批最多{BATCH_SIZE}条）")

    total = len(rows)
    processed_count = 0
    stocks_found = 0
    failed_count = 0
    round_robin = 0  # 全局递增，分跨多个 batch 仍保证均匀分配

    timeout = get_crawl_config()["findStocksTimeout"]

    for batch in batches:
        # 构建批量 prompt
        news_list = [{"title": row[3] or "", "summary": row[6] or ""} for row in batch]
        prompt = build_batch_prompt(news_list)
        batch_ids = [row[0] for row in batch]
        batch_titles = [row[3][:30] for row in batch]
        log(f"  -> 批次 {batch_ids}: {batch_titles}")

        text_blocks = None
        t0 = time.time()
        try:
            text_blocks = await call_async_raw(prompt, timeout=timeout)
        except Exception as e:
            elapsed = time.time() - t0
            log(f"  -> 批次 {batch_ids} LLM 调用异常: {e}（耗时 {elapsed:.1f}s）")
            failed_count += len(batch)
            processed_count += len(batch)
            continue
        elapsed = time.time() - t0
        log(f"  -> 批次 {batch_ids} LLM 调用完成，耗时 {elapsed:.1f}s")

        if not text_blocks:
            log(f"  -> 批次 {batch_ids} LLM 调用失败，跳过")
            failed_count += len(batch)
            processed_count += len(batch)
            continue

        report_text = "\n".join(text_blocks)
        stocks = parse_stocks_from_json(report_text)

        if not stocks:
            log(f"  -> 批次 {batch_ids} 解析失败，原始返回: {report_text[:500]}")
        else:
            log(f"  -> 批次 {batch_ids} 解析出 {len(stocks)} 只，示例: {stocks[:2]}")

        # news_index 缺失时用 round-robin 兜底（LLM 有时不返回 news_index）
        id_to_stocks: dict[int, list[dict]] = {bid: [] for bid in batch_ids}
        for s in stocks:
            idx = s.pop("news_index", None)
            if idx is not None and 0 <= idx < len(batch_ids):
                id_to_stocks[batch_ids[idx]].append(s)
            else:
                # round-robin 兜底：依次分配给 batch 内的各条新闻
                id_to_stocks[batch_ids[round_robin % len(batch_ids)]].append(s)
                round_robin += 1

        for row, importance_id in zip(batch, batch_ids):
            title = row[3] or ""
            news_stocks = id_to_stocks.get(importance_id, [])

            if not news_stocks:
                log(f"  -> id={importance_id} 未找到核心标的")
                processed_count += 1
                continue

            first_second = [s for s in news_stocks if s.get("tier") in ("第一梯队", "第二梯队")]
            if len(first_second) < len(news_stocks):
                log(f"  -> id={importance_id} 过滤第三梯队: {len(news_stocks)} → {len(first_second)} 只")

            if not first_second:
                log(f"  -> id={importance_id} 无第一/第二梯队标的，跳过入库")
                processed_count += 1
                continue

            if not dry_run:
                rows_to_insert = [{**s, "importance_id": importance_id} for s in first_second]
                inserted = insert_news_stocks(rows_to_insert)
                stocks_found += inserted
                log(f"  -> id={importance_id} 入库 {inserted} 只核心标的")
            else:
                stocks_found += len(first_second)
                log(f"  -> id={importance_id} [DRY-RUN]找到 {len(first_second)} 只")

            processed_count += 1

    log("=" * 60)
    log(f"完成: 待处理{total}条, 处理{processed_count}条, 失败{failed_count}条, 新增核心标的 {stocks_found} 只")
    return {"total": total, "processed": processed_count, "stocks_found": stocks_found, "failed": failed_count}