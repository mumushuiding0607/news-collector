"""
news_filter.py - Step 2: LLM 过滤（批量版）

读取最新批次（batch_id=MAX）且 is_useful=0 的新闻，
用 LLM 批量判断是否会引起市场波动。

批量大小由 crawl_config 统一配置的 llmBatchSize 字段控制（默认100）。
"""
import asyncio
import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

# -*- 在 import bootstrap 前解析 --db 参数 -*-
for i, arg in enumerate(sys.argv):
    if arg == "--db" and i + 1 < len(sys.argv):
        os.environ["NEWS_DB"] = sys.argv[i + 1]
        break

from script.bootstrap import *
from script.crawl.crawl_config import get_crawl_config
from script.crawl.crawl_db import get_unfiltered_batch, get_failed_batch, mark_useful, get_conn
from script.db.connection import put_conn, init_db
from llm import call_async_raw
from script.log import log as _log
from script.common.datetimeutil import now_iso

def log(msg: str):
    _log("news_filter", msg)


def _get_filter_prompt_file() -> Path:
    db_path = os.environ.get("NEWS_DB", "")
    if "ai_news" in db_path:
        return PROMPT_DIR / "AI新闻筛选.md"
    return PROMPT_DIR / "新闻筛选.md"

PROMPT_FILE = _get_filter_prompt_file()
_CACHED_TEMPLATE: str | None = None


def load_prompt_template() -> str:
    """加载提示词模板（缓存，避免每批次重新读文件 I/O）"""
    global _CACHED_TEMPLATE
    if _CACHED_TEMPLATE is None:
        _CACHED_TEMPLATE = PROMPT_FILE.read_text(encoding="utf-8") if PROMPT_FILE.exists() else ""
    return _CACHED_TEMPLATE


def build_batch_prompt(news_list: list[dict], template: str) -> str:
    items = []
    for i, news in enumerate(news_list, 1):
        item = f"{i}. {news.get('title', '')} | {news.get('summary', '')}"
        items.append(item)
    news_lines = "\n".join(items)
    return template.replace("<<news_list>>", news_lines)


def parse_batch_response(text_blocks: list[str], total: int, debug: bool = False) -> list[dict | None]:
    """解析 LLM 返回：只返回 id 列表 [1,3,5]，未返回的 id 默認為 will_flunctuate=false"""
    results: list[dict | None] = [{"will_flunctuate": False}] * total
    combined = "\n".join(text_blocks)

    combined_stripped = re.sub(r'```json\s*', '', combined)
    combined_stripped = re.sub(r'```\s*', '', combined_stripped)
    combined_stripped = combined_stripped.strip()

    m = re.search(r'\[\d[^]]*\]', combined_stripped)
    if m:
        try:
            arr = json.loads(m.group())
            if isinstance(arr, list):
                for item in arr:
                    if isinstance(item, int) and 1 <= item <= total:
                        results[item - 1] = {"will_flunctuate": True}
                return results
        except (json.JSONDecodeError, TypeError) as e:
            log(f"  [DEBUG] JSON解析失败: {e}, raw={m.group()[:100]}")

    # 回退：逐字符解析 JSON数组 [1,3,5]
    i = 0
    while i < len(combined_stripped):
        if combined_stripped[i] == '[':
            # 找到 [数字开头，尝试向前解析
            depth = 0
            j = i
            while j < len(combined_stripped):
                c = combined_stripped[j]
                if c == '[':
                    depth += 1
                elif c == ']':
                    depth -= 1
                    if depth == 0:
                        json_str = combined_stripped[i:j+1]
                        try:
                            arr = json.loads(json_str)
                            if isinstance(arr, list):
                                for item in arr:
                                    if isinstance(item, int) and 1 <= item <= total:
                                        results[item - 1] = {"will_flunctuate": True}
                                return results
                        except (json.JSONDecodeError, TypeError):
                            pass
                        break
                j += 1
        i += 1

    return results


async def process_batch_llm(
    news_batch: list[dict],
    timeout: int = 120,
    max_retries: int = 3,
    status_holder: dict | None = None,
) -> tuple[list[tuple[int, dict | None]], str]:
    """处理单个 LLM 过滤批次。

    失败降级策略：
    - call_async_raw 已内置 Stage 1（API 瞬时故障退避）和 Stage 2（真截断翻倍）。
    - 本函数只在外层再包一层"批次整体重试"：若单次 call_async_raw 返回全 None 或
      解析失败率 >50%，按 max_retries 退避重试；超过阈值后**整批降级为全部 useless**
      并返回，不抛异常——避免单批 LLM 故障卡死整条流水线。

    Returns:
        (results, status_str) 元组：
        - results: [(news_id, {"will_flunctuate": bool})] 每条新闻的判定
        - status_str: 本批次 LLM 调用情况的中文描述（用于日志）
    """
    template = load_prompt_template()
    prompt = build_batch_prompt(news_batch, template)

    # 输出格式：[1,3,5] ID 数组，~50 字符。2000 tokens 给 thinking + 输出充足缓冲。
    # 比 1000 更稳，比 4000 更快——是输出体积和延迟的折中点。
    MAX_TOKENS = 2000

    # 每次 call_async_raw 调用的详细记录
    # 每项: {"kind": str, "elapsed": float, "stage": 1|2, "max_tokens": int}
    call_log: list[dict] = []
    final_outcome = "unknown"
    success_attempt: int | None = None

    for attempt in range(1, max_retries + 1):
        if attempt > 1:
            log(f"  [RETRY] 第 {attempt} 次尝试，当前批次 {len(news_batch)} 条")

        llm_status: dict = {}
        t0 = time.time()
        raw_result = await call_async_raw(
            prompt, timeout=timeout, status_holder=llm_status,
        )
        elapsed = time.time() - t0

        # 收集本次调用的所有尝试（Stage 2 已删除，只有 attempts）
        for a in llm_status.get("attempts", []):
            call_log.append({
                "kind": a["kind"],
                "elapsed": a["elapsed"],
                "stage": 1,
                "max_tokens": a["max_tokens"],
            })

        if raw_result is None:
            last_kind = llm_status.get("last_kind", "unknown")
            # 按 kind 给"为什么 None"一个明确说法
            if last_kind == "timeout":
                reason = f"调用超时（>{timeout}s×{len(llm_status.get('attempts', []))}）"
            elif last_kind == "connection":
                reason = "连接错误（API 不可达）"
            elif last_kind == "empty":
                reason = "API 200 但 content 为空（多次返回无 text block）"
            elif last_kind == "decode":
                reason = "响应 JSON 解析失败"
            elif last_kind == "http_error":
                reason = "HTTP 非 200（参考 global.log）"
            else:
                reason = f"未知原因（kind={last_kind}）"
            log(f"  [RETRY] 第 {attempt} 次返回 None（耗时 {elapsed:.1f}s，{reason}）")
            final_outcome = f"第 {attempt} 次失败：{reason}"
            if attempt == max_retries:
                log(f"  [DOWNGRADE] 批次持续失败：{max_retries} 次外层重试全部 {last_kind}，标记 {len(news_batch)} 条为 useless")
                final_outcome = f"3 次重试全失败：{reason}，整批降级"
                if status_holder is not None:
                    status_holder["call_log"] = call_log
                    status_holder["final_outcome"] = "downgrade"
                return [(news["id"], {"will_flunctuate": False}) for news in news_batch], final_outcome
            await asyncio.sleep(5 * attempt)
            continue

        results = parse_batch_response(raw_result, len(news_batch))
        failed_count = sum(1 for r in results if r is None)

        if failed_count > len(results) // 2:
            log(f"  [RETRY] 解析失败率 {failed_count}/{len(results)}（耗时 {elapsed:.1f}s）")
            final_outcome = f"第 {attempt} 次解析失败率 {failed_count}/{len(results)}"
            if attempt == max_retries:
                log(f"  [DOWNGRADE] 解析持续失败，标记 {failed_count} 条为 useless")
                final_outcome = f"3 次重试解析仍失败：失败率 {failed_count}/{len(results)}，整批降级"
                if status_holder is not None:
                    status_holder["call_log"] = call_log
                    status_holder["final_outcome"] = "downgrade_parse"
                final_results = [{"will_flunctuate": False} if r is None else r for r in results]
                return [(news["id"], r) for news, r in zip(news_batch, final_results)], final_outcome
            await asyncio.sleep(5 * attempt)
            continue

        if attempt > 1:
            log(f"  [RETRY] 第 {attempt} 次成功（耗时 {elapsed:.1f}s）")
        success_attempt = attempt
        final_outcome = f"第 {attempt} 次成功（耗时 {elapsed:.1f}s，{len(call_log)} 次 LLM 调用）"
        # 把 None 也兜底为 False（单个 id 缺失视为"不会波动"）
        final_results = [{"will_flunctuate": False} if r is None else r for r in results]
        if status_holder is not None:
            status_holder["call_log"] = call_log
            status_holder["final_outcome"] = "ok"
        return [(news["id"], r) for news, r in zip(news_batch, final_results)], final_outcome

    # 理论上不会走到这里（max_retries 内必返回），但兜底
    if status_holder is not None:
        status_holder["call_log"] = call_log
        status_holder["final_outcome"] = "fallback"
    return [(news["id"], {"will_flunctuate": False}) for news in news_batch], "兜底：未知路径"


def pre_filter_news(news_list: list[dict], conn) -> tuple[list[dict], int]:
    """
    预过滤：标题过短的新闻直接标记为无用，不送 LLM。

    规则：标题少于 12 字的直接过滤。理由：
    - 标题信息密度过低，LLM 难以判断是否影响市场（容易误判）
    - 短标题多为导视/标题党/截断内容（如"短""早安""今日""继续关注"等）
    - 相比关键词规则（央视/体育/娱乐），字数过滤对所有来源中立，避免针对特定信源

    返回：(过滤后待处理列表, 预过滤数量)
    """
    MIN_TITLE_LEN = 12
    pre_filtered_count = 0

    for news in news_list:
        title = news["title"]
        if len(title) < MIN_TITLE_LEN:
            mark_useful(news["id"], useful=-1, commit=False, conn=conn)
            pre_filtered_count += 1

    if pre_filtered_count:
        conn.commit()

    filtered = [n for n in news_list if len(n["title"]) >= MIN_TITLE_LEN]
    return filtered, pre_filtered_count


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--retry", action="store_true", help="重试解析失败的新闻（is_useful=-1）")
    args = parser.parse_args()

    log("=" * 60)
    log(f"Step 2 [News Filter] start {now_iso()}" + (" [重试模式]" if args.retry else ""))

    cfg = get_crawl_config()
    batch_size = cfg["llmBatchSize"]
    timeout = cfg["newsFilterTimeout"]
    max_retries = cfg["llmMaxRetries"]
    log(f"批量大小: {batch_size}, 超时: {timeout}s, 最大重试: {max_retries}")

    init_db()
    conn = get_conn()

    rows = get_failed_batch(conn=conn) if args.retry else get_unfiltered_batch(conn=conn)
    log(f"待过滤新闻: {len(rows)} 条" + ("（解析失败重试）" if args.retry else ""))

    if not rows:
        log("没有待过滤的新闻，退出。")
        put_conn(conn)
        return

    news_list: list[dict] = [
        {"id": r[0], "source_name": r[1], "title": r[2] or "", "url": r[3],
         "summary": r[4] or "", "publish_time": r[5] or "", "content": r[6] or ""}
        for r in rows
    ]

    # 预过滤：明显的"无用"直接标记，不送 LLM（节省 ~15-25% 调用）
    # 规则保守：宁可漏判给 LLM，不要误杀
    news_list, pre_filtered_count = pre_filter_news(news_list, conn)
    if pre_filtered_count:
        log(f"预过滤标记 {pre_filtered_count} 条明显无用（不送 LLM）")

    import math
    batch_count = math.ceil(len(news_list) / batch_size)
    log(f"剩余送 LLM: {len(news_list)} 条 / {batch_count} 批")

    batches: list[list[dict]] = [news_list[i:i+batch_size] for i in range(0, len(news_list), batch_size)]
    log(f"分为 {len(batches)} 批处理（串行）")

    total_useful = total_useless = total_error = 0

    # 串行处理所有批次
    for idx, batch in enumerate(batches, 1):
        log(f"  — 批次 {idx}/{batch_count}，共 {len(batch)} 条 — 开始")
        t_start = time.time()
        batch_results, status_str = await process_batch_llm(
            batch, timeout=timeout, max_retries=max_retries, status_holder={},
        )
        elapsed = time.time() - t_start

        # 立即处理该批结果（按 id 找到对应新闻对象）
        batch_by_id = {n["id"]: n for n in batch}
        useful_items: list[tuple[int, str]] = []  # (id, title)
        useless_items: list[tuple[int, str]] = []
        parse_err_ids: list[int] = []
        for news_id, result in batch_results:
            title = batch_by_id.get(news_id, {}).get("title", "")

            if result is None:
                parse_err_ids.append(news_id)
                mark_useful(news_id, useful=-1, commit=False, conn=conn)
                total_error += 1
                continue

            will_flunctuate = result.get("will_flunctuate", False)

            if will_flunctuate is True:
                mark_useful(news_id, useful=1, commit=False, conn=conn)
                useful_items.append((news_id, title))
                total_useful += 1
            else:
                mark_useful(news_id, useful=-1, commit=False, conn=conn)
                useless_items.append((news_id, title))
                total_useless += 1
        conn.commit()

        # ===== 批次结果汇总（必须明确，不能不明不白） =====
        if useful_items:
            sample_parts = [f"id={i}「{t[:30]}」" for i, t in useful_items[:5]]
            sample = ", ".join(sample_parts)
            if len(useful_items) > 5:
                sample += f" ...等共 {len(useful_items)} 条"
            log(f"  — 批次 {idx}/{batch_count} 结果: ✅ 有用 {len(useful_items)} 条 | {sample}")
        else:
            log(f"  — 批次 {idx}/{batch_count} 结果: ⚠️ 0 条有用 — 全部 {len(batch)} 条均标记为无用 (无一条会引发市场波动)")

        if useless_items:
            useless_ids_sample = ", ".join(f"id={i}" for i, _ in useless_items[:3])
            if len(useless_items) > 3:
                useless_ids_sample += f" ...等共 {len(useless_items)} 条"
            log(f"  — 批次 {idx}/{batch_count} 详情: 无用 {len(useless_items)} 条 ({useless_ids_sample})")

        if parse_err_ids:
            log(f"  — 批次 {idx}/{batch_count} 解析异常: {len(parse_err_ids)} 条 (id={parse_err_ids[:5]})")

        log(f"  — 批次 {idx}/{batch_count} 耗时 {elapsed:.1f}s | LLM 状态: {status_str}")

    log("\n" + "=" * 60)
    log(f"过滤完成: 有用 {total_useful}, 无用 {total_useless}, 异常 {total_error}, 预过滤 {pre_filtered_count}")

    put_conn(conn)


if __name__ == "__main__":
    asyncio.run(main())