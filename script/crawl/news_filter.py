"""
news_filter.py - Step 2: LLM 过滤（批量版）

读取最新批次（batch_id=MAX）且 is_useful=0 的新闻，
用 LLM 批量判断是否会引起市场波动。

批量大小由 sources.json 的 llmBatchSize 字段控制（默认100）。
每批新闻打包成一条 prompt 调用一次 LLM，提升效率、节省 token。

调用机制：
  - 串行执行：严格禁止并发，每批等前一批结束后才执行
  - 重试机制：每批最多重试 max_retries 次（默认3）
"""
import asyncio
import argparse
import json
import re
from datetime import datetime
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.db import get_conn, init_db, get_unfiltered_batch, mark_useful, get_failed_batch
from llm import call_async_raw
from common.log import log as _log


BASE_DIR = Path(__file__).parent.parent.parent.resolve()
SOURCES_PATH = BASE_DIR / "config" / "sources.json"
PROMPT_FILE = BASE_DIR / "prompt" / "新闻筛选.md"


def log(msg: str):
    _log("news_filter", msg)


def load_prompt_template() -> str:
    if PROMPT_FILE.exists():
        return PROMPT_FILE.read_text(encoding="utf-8")
    return ""


def build_batch_prompt(news_list: list[dict], template: str) -> str:
    """
    将多条新闻拼接成 <<news_list>> 占位符内容。
    每条新闻格式：序号. [来源] 标题 | 发布时间 | 内容摘要
    """
    items = []
    for i, news in enumerate(news_list, 1):
        item = f"{i}. [{news.get('source_name', '')}] {news.get('title', '')} | {news.get('publish_time', '')} | {news.get('subtitle', '')}"
        items.append(item)
    news_lines = "\n".join(items)
    return template.replace("<<news_list>>", news_lines)


def parse_batch_response(text_blocks: list[str], total: int, debug: bool = True) -> list[dict | None]:
    """
    从 LLM 返回中解析批量评估结果。

    LLM 返回格式：JSON 数组 [{"id": 1, "will_flunctuate": true}, ...]
    返回 list，长度等于输入的 news 条目数，失败条目为 None。
    """
    results = [None] * total
    combined = "\n".join(text_blocks)

    print(f"  [DEBUG] 原始返回长度: {len(combined)} 字符")
    print(f"  [DEBUG] 原始返回（前1000字符）:\n{combined[:1000]}")
    print(f"  [DEBUG] text_blocks 数量: {len(text_blocks)}")

    # 策略1：找 JSON 数组 [...]  先整体合并再匹配
    combined_stripped = re.sub(r'```json\s*', '', combined)
    combined_stripped = re.sub(r'```\s*', '', combined_stripped)
    combined_stripped = combined_stripped.strip()

    print(f"  [DEBUG] 清理后内容（前500字符）: {combined_stripped[:500]}")

    m = re.search(r'\[[\s\S]*\]', combined_stripped)
    if m:
        try:
            arr = json.loads(m.group())
            if isinstance(arr, list):
                id_map = {item["id"]: item for item in arr if "id" in item}
                results = [id_map.get(i + 1) for i in range(total)]
                if debug:
                    print(f"  [DEBUG] 数组解析成功，命中 {sum(1 for r in results if r is not None)}/{total}")
                return results
        except json.JSONDecodeError as e:
            if debug:
                print(f"  [DEBUG] 数组解析失败: {e}")

    # 策略2：括号计数解析所有 JSON 对象（逐 block 合并后解析）
    i = 0
    while i < len(combined_stripped):
        if combined_stripped[i] == '{':
            start = i
            depth = 0
            j = i
            while j < len(combined_stripped):
                if combined_stripped[j] == '{':
                    depth += 1
                elif combined_stripped[j] == '}':
                    depth -= 1
                    if depth == 0:
                        json_str = combined_stripped[start:j+1]
                        try:
                            obj = json.loads(json_str)
                            if "id" in obj and "will_flunctuate" in obj:
                                idx = obj["id"] - 1
                                if 0 <= idx < total and results[idx] is None:
                                    results[idx] = {"will_flunctuate": obj["will_flunctuate"]}
                        except json.JSONDecodeError:
                            pass
                        i = j
                        break
                j += 1
        i += 1

    found = sum(1 for r in results if r is not None)
    print(f"  [DEBUG] 括号计数解析命中 {found}/{total}")

    if found == 0:
        print(f"  [DEBUG] 解析失败！检查返回内容是否包含 will_flunctuate 字段")
        print(f"  [DEBUG] 返回内容中是否包含 'will_flunctuate': {combined_stripped.__contains__('will_flunctuate')}")
        print(f"  [DEBUG] 返回内容中是否包含 'id': {combined_stripped.__contains__('id')}")
        print(f"  [DEBUG] 返回内容中是否包含 '[': {combined_stripped.__contains__('[')}")

    return results


async def process_batch_llm(news_batch: list[dict], timeout: int = 120, max_retries: int = 3) -> list[tuple[int, dict | None]]:
    """
    单批次 LLM 调用，带重试机制。

    Args:
        news_batch: 本批次新闻列表
        max_retries: 最大重试次数，默认3

    Returns:
        [(news_id, result), ...]，result 为 None 表示失败/超时
    """
    template = load_prompt_template()
    prompt = build_batch_prompt(news_batch, template)

    for attempt in range(1, max_retries + 1):
        if attempt > 1:
            log(f"  [RETRY] 第 {attempt} 次尝试，当前批次 {len(news_batch)} 条")

        raw_result = await call_async_raw(prompt, timeout=timeout)

        print(f"  [DEBUG] call_async_raw 返回类型: {type(raw_result)}, 是否为 None: {raw_result is None}")
        if raw_result is not None:
            print(f"  [DEBUG] text_blocks 数量: {len(raw_result)}")
            for idx, block in enumerate(raw_result):
                print(f"  [DEBUG] block[{idx}] 长度: {len(block)}, 内容: {block[:200]}")

        if raw_result is None:
            log(f"  [RETRY] 第 {attempt} 次返回 None {"(最后一次)" if attempt == max_retries else ""}")
            if attempt == max_retries:
                return [(news["id"], None) for news in news_batch]
            await asyncio.sleep(5 * attempt)  # 递增退避
            continue

        results = parse_batch_response(raw_result, len(news_batch))
        failed_count = sum(1 for r in results if r is None)

        if failed_count > len(results) // 2:
            log(f"  [RETRY] 解析失败率 {failed_count}/{len(results)}，{"(最后一次)" if attempt == max_retries else "重试"}")
            if attempt == max_retries:
                return [(news["id"], None) for news in news_batch]
            await asyncio.sleep(5 * attempt)
            continue

        # 成功
        if attempt > 1:
            log(f"  [RETRY] 第 {attempt} 次成功")
        return [(news["id"], r) for news, r in zip(news_batch, results)]


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--retry", action="store_true", help="重试解析失败的新闻（is_useful=-1）")
    args = parser.parse_args()

    log("=" * 60)
    log(f"Step 2 [News Filter] start {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}" + (" [重试模式]" if args.retry else ""))

    sources_data = json.loads(SOURCES_PATH.read_text(encoding="utf-8"))

    batch_size = sources_data.get("llmBatchSize", 100)
    timeout = sources_data.get("llmTimeout", 120)
    max_retries = sources_data.get("llmMaxRetries", 3)
    log(f"批量大小: {batch_size}, 超时: {timeout}s, 最大重试: {max_retries}")

    init_db()
    conn = get_conn()

    rows = get_failed_batch(conn=conn) if args.retry else get_unfiltered_batch(conn=conn)
    log(f"待过滤新闻: {len(rows)} 条" + ("（解析失败重试）" if args.retry else ""))

    if not rows:
        log("没有待过滤的新闻，退出。")
        conn.close()
        return

    news_list: list[dict] = [
        {"id": r[0], "source_name": r[1], "title": r[2] or "", "url": r[3],
         "subtitle": r[4] or "", "publish_time": r[5] or "", "content": r[6] or ""}
        for r in rows
    ]

    import math
    batch_count = math.ceil(len(news_list) / batch_size)
    call_count = batch_count
    log(f"预计 LLM 调用次数: {call_count} 次（{len(news_list)} 条 / 批量 {batch_size} = {batch_count} 批）")

    batches: list[list[dict]] = [news_list[i:i+batch_size] for i in range(0, len(news_list), batch_size)]
    log(f"分为 {len(batches)} 批处理")

    total_useful = 0
    total_useless = 0
    total_error = 0

    # 串行执行：显式串行锁，禁止任何并发
    # asyncio.Semaphore(1) 确保同一时刻只有一批在执行
    serial_lock = asyncio.Semaphore(1)

    for batch_idx, batch in enumerate(batches, 1):
        async with serial_lock:
            log(f"  — 批次 {batch_idx}/{batch_count}，共 {len(batch)} 条 —")
            batch_results = await process_batch_llm(batch, timeout=timeout, max_retries=max_retries)

            for news_id, result in batch_results:
                title = next((n["title"] for n in batch if n["id"] == news_id), "")

                if result is None:
                    log(f"  [WARN] id={news_id} LLM 返回异常，跳过")
                    mark_useful(news_id, useful=-1, commit=False, conn=conn)
                    total_error += 1
                    conn.commit()
                    continue

                will_flunctuate = result.get("will_flunctuate", False)

                if will_flunctuate is True:
                    mark_useful(news_id, useful=1, commit=False, conn=conn)
                    total_useful += 1
                    log(f"  [USEFUL] id={news_id} | {title[:40]}")
                else:
                    mark_useful(news_id, useful=-1, commit=False, conn=conn)
                    total_useless += 1
                    log(f"  [USELESS] id={news_id} | {title[:40]}")

                conn.commit()

    log("\n" + "=" * 60)
    log(f"过滤完成: 有用 {total_useful}, 无用 {total_useless}, 异常 {total_error}")
    log(f"LLM 总调用次数: {call_count} 次")

    conn.close()


if __name__ == "__main__":
    asyncio.run(main())