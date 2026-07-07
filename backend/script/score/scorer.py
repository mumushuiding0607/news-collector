"""
scorer.py - 新闻评分模块（批量版）

读取 primary_sources 中 status='read' 且 is_useful=1 的新闻，
**批量喂给 LLM 一次评估多条**，返回结构化数组后切回每条入 importance 表。

设计要点：
  - LLM 调用必须串行（约束：API RPS 上限，并发无收益）
  - 批量大小受质量约束严格控制（默认 5，硬上限 10）
  - 批量解析失败时自动回退单条重试，保证不丢数据
  - 单条与批量走同一套 prompt 模板（N=1 视为长度为 1 的数组）

使用：
  python scorer.py [--limit N] [--batch-size N] [--dry-run]
"""

import argparse
import asyncio
import json
import re
import sys
import time
from pathlib import Path

# 在 import bootstrap 前解析 --type 参数（必须最早执行）
from script.bootstrap import parse_db_arg, is_ai_news_db
sys.argv = parse_db_arg(sys.argv)

from script.bootstrap import *


# AI 新闻短名映射（内联于 _get_ai 使用）
from script.db import get_unread, mark_scored, insert_importance
from script.db.sectors import normalize
from script.crawl.crawl_config import get_crawl_config
from llm import call_async_raw
from script.log import log as _log, init_log
from script.common.datetimeutil import now_iso, is_today

# ---------------------------------------------------------------------------
# 路径与常量
# ---------------------------------------------------------------------------

PROMPT_FILE = PROMPT_DIR / ("AI事件评估.md" if is_ai_news_db() else "事件评估.md")
_CACHED_TEMPLATE: str | None = None

# 批量评分质量控制：
#   质量优先 > 速度优先。批量越大 LLM 越容易"偷懒"输出趋同结果，
#   实测前先用 5；若发现批量结果与单条评估明显偏差，下调到 3。
DEFAULT_BATCH_SIZE = 5
HARD_MAX_BATCH_SIZE = 10
CONTENT_TRUNCATE = 3000  # 每条新闻内容截断长度
# 不限制 max_tokens：让 LLM 一次写完 thinking + 5 条新闻 JSON。
# 限制反而更慢——历史曾加过 Stage 2 翻倍重试（4000→8000→16000→32000），
# 实际是纯浪费：API 慢时每一级都先吃 3×300s=900s 才升级，worst case 60 min/批，
# 且每次重试都消耗 token 无产出。已删 Stage 2（client.py）。
# None = 完全不限制，API 端让 LLM 自然输出。
BATCH_MAX_TOKENS = None
THINKING_BUDGET_TOKENS = None  # 不限制（API 也忽略此参数）

# ---------------------------------------------------------------------------
# 字段名映射（短名 → 长名）
#
# 短名给 LLM 节省 token；长名给 DB / 业务层使用（兼容历史数据）。
# _get() 会先认短名再认长名，所以混合输入（部分新、部分旧）也不会挂。
# ---------------------------------------------------------------------------

_SHORT_TO_LONG: dict[str, str] = {
    "wf": "will_flunctuate",
    "sum": "summary",
    "sec": "related_sectors",
    "score": "importance_score",
    "dir": "direction",
    "intst": "intensity",
    "chg": "expected_change",
    "dur": "duration",
    "lvl": "expectation_level",
    "md": "market_mode",
}
_LONG_TO_SHORT: dict[str, str] = {v: k for k, v in _SHORT_TO_LONG.items()}


def _get(item: dict, long_key: str, default=None):
    """从 LLM 返回 dict 取值：先认短名（省 token 的新格式），再认长名（向前兼容）。"""
    short = _LONG_TO_SHORT.get(long_key)
    if short is not None and short in item:
        return item[short]
    return item.get(long_key, default)


def _get_ai(item: dict, long_key: str, default=None):
    """从 LLM 返回 dict 取值：先认短名，再认长名。"""
    short_map = {"score": "s", "tech_novelty": "tn", "monetization": "m",
                 "domains": "ad", "highlights": "kh", "reason": "r"}
    short = short_map.get(long_key)
    if short is not None and short in item:
        return item[short]
    return item.get(long_key, default)


def _build_ai_result(result: dict) -> dict:
    """将通用 result 转换为 importance_ai 格式。"""
    llm_item = result.get("_llm_item", {})
    return {
        "news_id": result["news_id"],
        "source_name": result["source_name"],
        "title": result.get("title", ""),
        "url": result.get("url", ""),
        "publish_time": result.get("publish_time", ""),
        "summary": result.get("summary", ""),
        "score": _get_ai(llm_item, "score", 0),
        "tech_novelty": _get_ai(llm_item, "tech_novelty"),
        "monetization": _get_ai(llm_item, "monetization", ""),
        "domains": _get_ai(llm_item, "domains", ""),
        "highlights": _get_ai(llm_item, "highlights", ""),
        "reason": _get_ai(llm_item, "reason", ""),
    }


def log(msg: str):
    _log("scorer", msg)


# ---------------------------------------------------------------------------
# 提示词构建（批量版：N=1 也走批量格式，单条模板已废弃）
# ---------------------------------------------------------------------------

def load_prompt_template() -> str:
    """加载提示词模板（缓存）"""
    global _CACHED_TEMPLATE
    if _CACHED_TEMPLATE is None:
        _CACHED_TEMPLATE = PROMPT_FILE.read_text(encoding="utf-8") if PROMPT_FILE.exists() else ""
    return _CACHED_TEMPLATE


def assemble_content(source_name: str, title: str, summary: str, content: str) -> str:
    """
    组装发送给 LLM 的内容。

    优先级：content > summary > title
    LLM 会根据实际内容判断是否会引起市场波动。
    """
    if content and len(content.strip()) >= 20:
        return content[:CONTENT_TRUNCATE]
    parts = []
    if summary and len(summary.strip()) >= 10:
        parts.append(f"[摘要] {summary.strip()}")
    if title and len(title.strip()) >= 5:
        parts.append(f"[标题] {title.strip()}")
    return "\n".join(parts) if parts else ""


def build_batch_prompt(items: list[dict]) -> str:
    """构建批量评分 prompt。

    items: 每条含 seq / source_name / title / publish_time / content（已 assemble）
    """
    template = load_prompt_template()
    blocks = []
    for it in items:
        blocks.append(
            f"--- NEWS {it['seq']} ---\n"
            f"- 来源: {it.get('source_name', '')}\n"
            f"- 标题: {it.get('title', '') or ''}\n"
            f"- 发布时间: {it.get('publish_time', '') or ''}\n"
            f"- 内容:\n{it.get('content', '')}\n"
        )
    news_list_text = "\n".join(blocks)
    return template.replace("<<news_list>>", news_list_text)


# ---------------------------------------------------------------------------
# 板块归一化
# ---------------------------------------------------------------------------

def normalize_sectors(raw_sectors: str) -> list[dict]:
    if not raw_sectors:
        return []
    return normalize(raw_sectors)


def format_normalized_sectors(sector_list: list[dict]) -> str:
    if not sector_list:
        return ""
    return "|".join(s["name"] for s in sector_list if s.get("normalized"))


# ---------------------------------------------------------------------------
# LLM 响应解析
# ---------------------------------------------------------------------------

def parse_batch_response(text_blocks: list[str], expected_len: int) -> list[dict] | None:
    """从 LLM 返回的 text blocks 中解析 JSON 数组。

    成功条件：必须是数组、长度等于 expected_len。任一不满足返回 None 触发回退。
    """
    if not text_blocks:
        return None
    combined = "\n".join(text_blocks).strip()
    # 去 markdown 代码块
    combined = re.sub(r"^```json\s*", "", combined, flags=re.MULTILINE)
    combined = re.sub(r"^```\s*$", "", combined, flags=re.MULTILINE).strip()

    # 找到最外层数组
    m = re.search(r"\[[\s\S]*\]", combined)
    if not m:
        return None
    try:
        arr = json.loads(m.group())
    except json.JSONDecodeError:
        return None
    if not isinstance(arr, list):
        return None
    if len(arr) != expected_len:
        log(f"  [WARN] LLM 返回 {len(arr)} 条，预期 {expected_len} 条，触发回退")
        return None
    return arr


def build_result_dict(news_meta: dict, llm_item: dict) -> dict:
    """把 LLM 单条结果 + DB 元信息组合成入库 dict（沿用旧 process_news 输出结构）。

    字段名通过 _get() 兼容短名（新格式）和长名（历史数据）。
    AI新闻用 v 字段判断价值，股市新闻用 will_flunctuate 判断是否引起波动。
    """
    # AI 新闻：v=true 才入库
    if is_ai_news_db():
        is_valuable = _get(llm_item, "v", False)
        if is_valuable is False:
            return {"skipped": True, "reason": "no_value", "news_id": news_meta["news_id"]}
    else:
        # 股市新闻：will_flunctuate 才入库
        will_flunctuate = _get(llm_item, "will_flunctuate", False)
        if will_flunctuate is False:
            return {"skipped": True, "reason": "no_fluctuation", "news_id": news_meta["news_id"]}

    normalized = normalize_sectors(_get(llm_item, "related_sectors", ""))
    result_dict = {
        "skipped": False,
        "news_id": news_meta["news_id"],
        "batch_id": news_meta["batch_id"],
        "source_name": news_meta["source_name"],
        "title": news_meta["title"],
        "url": news_meta["url"],
        "publish_time": news_meta["publish_time"],
        "summary": _get(llm_item, "summary", ""),
        "related_sectors": format_normalized_sectors(normalized),
        "importance_score": _get(llm_item, "importance_score", 0),
        "reason": _get(llm_item, "reason", ""),
        "direction": _get(llm_item, "direction", ""),
        "intensity": _get(llm_item, "intensity", 0),
        "expected_change": _get(llm_item, "expected_change", ""),
        "duration": _get(llm_item, "duration", ""),
        "expectation_level": _get(llm_item, "expectation_level", ""),
        "market_mode": _get(llm_item, "market_mode", ""),
    }
    result_dict["_llm_item"] = llm_item
    return result_dict


# ---------------------------------------------------------------------------
# 预过滤（LLM 调用前的廉价跳过判断）
# ---------------------------------------------------------------------------

def pre_filter(news_row: tuple) -> tuple[dict | None, dict | None]:
    """
    返回 (news_meta, skip_result)：

      skip_result != None 表示该条无需调 LLM（直接 mark_scored）；
      news_meta != None 表示该条要进 LLM 批次。
    """
    news_id, source_name, title, url, summary, publish_time, content, batch_id = news_row

    if not publish_time or not is_today(publish_time):
        reason = "无日期" if not publish_time else f"非当天 {publish_time}"
        log(f"  [SKIP] id={news_id} {reason}")
        return None, {"skipped": True, "reason": "no_date_or_not_today", "news_id": news_id}

    effective_content = assemble_content(source_name, title, summary, content or "")
    if not effective_content or len(effective_content.strip()) < 5:
        log(f"  [SKIP] id={news_id} 无可评估内容")
        return None, {"skipped": True, "reason": "no_content", "news_id": news_id}

    return {
        "news_id": news_id,
        "batch_id": batch_id,
        "source_name": source_name,
        "title": title or "",
        "url": url,
        "publish_time": publish_time,
        "content": effective_content,
    }, None


# ---------------------------------------------------------------------------
# 批量评分主路径
# ---------------------------------------------------------------------------

async def call_llm_batch(items: list[dict]) -> list[dict] | None:
    """串行调用一次 LLM 评估整个 batch。失败返回 None，由上层标记 batch_failed。"""
    if not items:
        return []
    cfg = get_crawl_config()
    timeout = cfg["scorerTimeout"]
    # 拼 seq（从 1 开始）
    seqed = [{**it, "seq": idx + 1} for idx, it in enumerate(items)]
    prompt = build_batch_prompt(seqed)
    t0 = time.time()
    try:
        text_blocks = await call_async_raw(
            prompt, timeout=timeout,
        )
    except Exception as e:
        elapsed = time.time() - t0
        log(f"  [WARN] 批量 LLM 调用异常: {type(e).__name__}: {e}（耗时 {elapsed:.1f}s）")
        return None
    elapsed = time.time() - t0
    log(f"  [LLM] scorer 调用完成，耗时 {elapsed:.1f}s")
    return parse_batch_response(text_blocks, expected_len=len(items)) if text_blocks else None


async def process_batch(news_rows: list[tuple]) -> list[dict]:
    """
    处理一组 news_rows，返回 result dict 列表（顺序与输入对齐）。

    路径：预过滤 → 批量 LLM → 若失败，标记 batch_failed（**不再回退单条**）。
    失败项不调 mark_scored，保留 status='read' 供 --retry 重跑。

    历史变更：旧版 FALLBACK 单条模式（5 条各跑一遍 LLM）会导致一个失败的 batch
    耗时从 15 min（Stage 1 重试）膨胀到 90 min（5 × Stage 1 重试）。改为
    整批标记失败后，由后续 --retry 单独处理，单批失败耗时恒定 ~15 min。
    """
    # 预过滤
    results: list[dict | None] = [None] * len(news_rows)
    pending: list[tuple[int, dict]] = []  # [(orig_idx, meta), ...]
    for i, row in enumerate(news_rows):
        meta, skip = pre_filter(row)
        if skip is not None:
            results[i] = skip
        else:
            pending.append((i, meta))

    if not pending:
        return [r for r in results if r is not None]

    # 一次批量调用
    metas = [m for _, m in pending]
    llm_items = await call_llm_batch(metas)

    if llm_items is None:
        # 批量失败 → 整批标记为待重试（不再回退单条，避免放大耗时）
        log(f"  [BATCH_FAIL] 批量 LLM 失败，{len(pending)} 条标记为待重试（status 保持 read）")
        for orig_idx, meta in pending:
            results[orig_idx] = {
                "skipped": True, "reason": "batch_failed", "news_id": meta["news_id"],
            }
    else:
        # 批量成功，按序号映射
        for (orig_idx, meta), llm_item in zip(pending, llm_items):
            results[orig_idx] = build_result_dict(meta, llm_item)

    return [r for r in results if r is not None]


# ---------------------------------------------------------------------------
# 入库
# ---------------------------------------------------------------------------

def commit_result(result: dict, dry_run: bool) -> str:
    """把单条 result 落库，返回简短状态码（'ok' / 'skip' / 'failed' / 'failed_pending'）。

    设计要点：
    - batch_failed: 不调用 mark_scored，保留 status='read'，下次自动重试
    - no_date_or_not_today / no_content: 合法跳过，mark_scored 标记完成
    - 正常评分: 写 importance 表 + mark_scored
    """
    news_id = result["news_id"]
    if result["skipped"]:
        reason = result.get("reason", "")
        if reason == "batch_failed":
            # 评分失败：保持 status='read'，下次运行自动重试
            log(f"  -> id={news_id} 评分失败(status 保持 read，等下次重试)")
            return "failed_pending"
        if not dry_run:
            mark_scored(news_id)
        log(f"  -> id={news_id} 已跳过({reason}) [OK]")
        return "skip"
    if not dry_run:
        if is_ai_news_db():
            from script.db import insert_ai
            insert_ai(_build_ai_result(result))
        else:
            insert_importance(result)
        mark_scored(news_id)
    log(f"  -> id={news_id} 评分={result.get('importance_score', 0)} "
        f"板块={result.get('related_sectors', '')[:40]} [OK]")
    return "ok"


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

def main():
    init_log()

    parser = argparse.ArgumentParser(description="新闻评分模块")
    parser.add_argument("--limit", type=int, default=50,
                        help=f"每轮拉取的总条数（默认 50，配合 --batch-size 拆批）")
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE,
                        help=f"单批 LLM 评分条数（默认 {DEFAULT_BATCH_SIZE}，硬上限 {HARD_MAX_BATCH_SIZE}，控制以保质量）")
    parser.add_argument("--dry-run", action="store_true", help="仅模拟，不写入数据库")
    parser.add_argument("--max-cycles", type=int, default=100, help="最大循环次数（默认100）")
    parser.add_argument("--find-stocks", action="store_true", help="核心标的发现模式")
    parser.add_argument("--min-score", type=int, default=6, help="find-stocks 最低评分门槛（默认6）")
    args = parser.parse_args()

    if args.find_stocks:
        from script.stock.find_stocks_logic import findStocks
        findStocks(dry_run=args.dry_run, min_score=args.min_score)
        return

    batch_size = max(1, min(args.batch_size, HARD_MAX_BATCH_SIZE))
    if batch_size != args.batch_size:
        log(f"[WARN] batch_size 被钳制到 [1, {HARD_MAX_BATCH_SIZE}] 区间: {args.batch_size} -> {batch_size}")

    # scorer 开始前先查一次待处理条数（不占用主循环的 limit 名额）
    pre_check = get_unread(limit=10000)
    log("=" * 60)
    log(f"News scoring start {now_iso()}")
    log(f"待处理: {len(pre_check)} 条（实际以循环拉取为准）")
    log(f"Mode: {'DRY-RUN' if args.dry_run else 'LIVE'}")
    log(f"每轮拉取: {args.limit}, 批量大小: {batch_size}")
    log("=" * 60)

    asyncio.run(_run_main_loop(
        limit=args.limit, batch_size=batch_size,
        max_cycles=args.max_cycles, dry_run=args.dry_run,
    ))


async def _run_main_loop(limit: int, batch_size: int, max_cycles: int, dry_run: bool) -> None:
    cycle = 0
    total_ok = total_skip = total_failed = 0

    while cycle < max_cycles:
        cycle += 1
        all_news = get_unread(limit=limit)
        if not all_news:
            log(f"\n[循环 {cycle}] 没有待处理的新闻，退出。")
            break

        log(f"\n[循环 {cycle}/{max_cycles}] 待处理新闻: {len(all_news)} 条")

        # 切批
        for batch_idx in range(0, len(all_news), batch_size):
            batch_rows = all_news[batch_idx:batch_idx + batch_size]
            log(f"  — 批次 {batch_idx // batch_size + 1}, {len(batch_rows)} 条 —")

            try:
                results = await process_batch(batch_rows)
            except Exception as e:
                log(f"  !!! 批次异常: {type(e).__name__}: {e}")
                log(f"  当前统计: 评分入库 {total_ok}, 跳过 {total_skip}, 失败 {total_failed}")
                return

            for r in results:
                status = commit_result(r, dry_run=dry_run)
                if status == "ok":
                    total_ok += 1
                elif status == "skip":
                    total_skip += 1
                elif status == "failed_pending":
                    total_failed += 1
                else:
                    total_failed += 1

    log("=" * 60)
    log(f"完成: 评分入库 {total_ok}, 跳过 {total_skip}, 评分失败(待重试) {total_failed}")
    log(f"总循环: {cycle}")


if __name__ == "__main__":
    main()
