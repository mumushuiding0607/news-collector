"""
news_filter_ai.py - AI 新闻专用评分脚本

AI 新闻量少，默认全部有效，只做评分不入库 primary_sources.is_useful。
直接批量送 LLM 评分，评分结果写入 importance_ai 表。
"""
import argparse
import asyncio
import json
import re
import sys
import time

from script.bootstrap import parse_db_arg
sys.argv = parse_db_arg(sys.argv)

from script.bootstrap import *
from script.crawl.crawl_config import get_crawl_config
from script.crawl.crawl_db import get_unfiltered_batch, mark_useful, get_conn
from script.db.connection import put_conn, init_db
from llm import call_async_raw
from script.log import log as _log
from script.common.datetimeutil import now_iso


def log(msg: str):
    _log("news_filter_ai", msg)


PROMPT_FILE = PROMPT_DIR / "AI新闻筛选.md"
_CACHED_TEMPLATE: str | None = None


def load_prompt_template() -> str:
    global _CACHED_TEMPLATE
    if _CACHED_TEMPLATE is None:
        _CACHED_TEMPLATE = PROMPT_FILE.read_text(encoding="utf-8") if PROMPT_FILE.exists() else ""
    return _CACHED_TEMPLATE


def build_batch_prompt(news_list: list[dict], template: str) -> str:
    """构建批量 prompt。有摘要用标题+摘要，无摘要只用标题。"""
    items = []
    for i, news in enumerate(news_list, 1):
        title = news.get("title", "")
        summary = news.get("summary", "")
        if summary and summary.strip():
            item = f"{i}. {title} | {summary}"
        else:
            item = f"{i}. {title}"
        items.append(item)
    news_lines = "\n".join(items)
    return template.replace("<<news_list>>", news_lines)


def parse_batch_response(text_blocks: list[str], total: int) -> list[dict | None]:
    """解析 LLM 返回的 JSON 数组。"""
    results: list[dict | None] = [None] * total
    combined = "\n".join(text_blocks)
    combined = re.sub(r'```json\s*', '', combined)
    combined = re.sub(r'```\s*', '', combined).strip()

    m = re.search(r'\[[\s\S]*\]', combined)
    if m:
        try:
            arr = json.loads(m.group())
            if isinstance(arr, list):
                for item in arr:
                    if isinstance(item, dict) and "id" in item:
                        idx = item["id"]
                        if isinstance(idx, int) and 1 <= idx <= total:
                            results[idx - 1] = item
                return results
        except (json.JSONDecodeError, TypeError):
            pass
    return results


async def process_batch_llm(
    news_batch: list[dict],
    timeout: int = 40,
    max_retries: int = 3,
) -> tuple[list[tuple[int, dict | None]], str]:
    template = load_prompt_template()
    prompt = build_batch_prompt(news_batch, template)

    for attempt in range(1, max_retries + 1):
        if attempt > 1:
            log(f"  [RETRY] 第 {attempt} 次尝试，当前批次 {len(news_batch)} 条")

        llm_status: dict = {}
        t0 = time.time()
        raw_result = await call_async_raw(
            prompt, timeout=timeout, status_holder=llm_status,
        )
        elapsed = time.time() - t0

        if raw_result is None:
            reason = llm_status.get("last_kind", "unknown")
            log(f"  [RETRY] 第 {attempt} 次返回 None（{reason}，耗时 {elapsed:.1f}s）")
            if attempt == max_retries:
                return [(news["id"], None) for news in news_batch], f"3次重试全失败"
            await asyncio.sleep(5 * attempt)
            continue

        parsed = parse_batch_response(raw_result, len(news_batch))
        failed_count = sum(1 for r in parsed if r is None)

        if failed_count > len(parsed) // 2:
            log(f"  [RETRY] 解析失败率 {failed_count}/{len(parsed)}（耗时 {elapsed:.1f}s）")
            if attempt == max_retries:
                final_results = [r if r is not None else {} for r in parsed]
                return [(news["id"], r) for news, r in zip(news_batch, final_results)], f"3次重试解析仍失败"
            await asyncio.sleep(5 * attempt)
            continue

        final_results = [r if r is not None else {} for r in parsed]
        return [(news["id"], r) for news, r in zip(news_batch, final_results)], f"成功（耗时 {elapsed:.1f}s）"

    return [(news["id"], None) for news in news_batch], "兜底"


def build_ai_result(news: dict, llm_item: dict) -> dict:
    """将 LLM 返回 dict + DB元信息组合成 importance_ai 入库格式。"""
    return {
        "news_id": news["id"],
        "source_name": news.get("source_name", ""),
        "title": news.get("title", ""),
        "url": news.get("url", ""),
        "publish_time": news.get("publish_time", ""),
        "summary": news.get("summary", ""),
        "score": llm_item.get("s", 0),
        "tech_novelty": llm_item.get("tn"),
        "monetization": "",
        "domains": llm_item.get("ad", ""),
        "highlights": llm_item.get("kh", ""),
        "reason": llm_item.get("r", ""),
    }


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--retry", action="store_true", help="重试失败的新闻")
    args = parser.parse_args()

    log("=" * 60)
    log(f"[News Filter AI] start {now_iso()}" + (" [重试模式]" if args.retry else ""))

    cfg = get_crawl_config()
    batch_size = cfg.get("newsFilterBatchSize", cfg["llmBatchSize"])
    timeout = cfg["newsFilterTimeout"]
    max_retries = cfg["llmMaxRetries"]
    log(f"批量大小: {batch_size}, 超时: {timeout}s, 最大重试: {max_retries}")

    init_db()
    conn = get_conn()

    rows = get_unfiltered_batch(conn=conn)
    log(f"待评分新闻: {len(rows)} 条")

    if not rows:
        log("没有待评分的新闻，退出。")
        put_conn(conn)
        return

    news_list: list[dict] = [
        {"id": r[0], "source_name": r[1], "title": r[2] or "", "url": r[3],
         "summary": r[4] or "", "publish_time": r[5] or ""}
        for r in rows
    ]

    import math
    batch_count = math.ceil(len(news_list) / batch_size)
    log(f"送 LLM 评分: {len(news_list)} 条 / {batch_count} 批")

    batches: list[list[dict]] = [news_list[i:i+batch_size] for i in range(0, len(news_list), batch_size)]

    total_scored = total_failed = 0

    for idx, batch in enumerate(batches, 1):
        log(f"  — 批次 {idx}/{batch_count}，共 {len(batch)} 条 — 开始")
        t_start = time.time()
        batch_results, status_str = await process_batch_llm(batch, timeout=timeout, max_retries=max_retries)
        elapsed = time.time() - t_start

        from script.db import insert_ai
        batch_by_id = {n["id"]: n for n in batch}

        for news_id, llm_item in batch_results:
            news = batch_by_id.get(news_id, {})
            title = news.get("title", "")

            if llm_item:
                result = build_ai_result(news, llm_item)
                ok = insert_ai(result, conn=conn, commit=False)
                if ok:
                    mark_useful(news_id, useful=1, commit=False, conn=conn)
                    total_scored += 1
                else:
                    mark_useful(news_id, useful=-1, commit=False, conn=conn)
                    total_failed += 1
            else:
                mark_useful(news_id, useful=-1, commit=False, conn=conn)
                total_failed += 1

        conn.commit()

        scored_sample = ", ".join(f"id={n['id']}「{batch_by_id[n['id']]['title'][:20]}...」" for _, n in [(i, batch_by_id[r[0]]) for i, r in enumerate(batch_results) if r[1]][:3])
        log(f"  — 批次 {idx}/{batch_count} 完成: 评分 {len([r for r in batch_results if r[1]])} 条 | {status_str}")

    log("\n" + "=" * 60)
    log(f"评分完成: 成功 {total_scored}, 失败 {total_failed}")

    put_conn(conn)


if __name__ == "__main__":
    asyncio.run(main())
