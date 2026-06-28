"""
anomaly_news/hot_news.py - 热点新闻简报生成（基于 importance 数据，两阶段方案）

Stage 1: 每条 importance 记录 → 生成结构化分篇摘要
Stage 2: 汇总所有分篇摘要 → 生成最终热点新闻报告
"""
import asyncio
import json
import math
import re
from pathlib import Path

from script.log import log as _log, init_log
from script.db import get_positive_by_date, get_latest_importance_date
from script.db.anomaly_summary_db import save_summary
from script.llm.client import call_async_raw, parse_response


def log(msg: str):
    _log("hot_news", msg)


PROMPT_STAGE1 = Path(__file__).parent.parent.parent / "prompt" / "热点新闻_阶段1_分篇摘要.md"
PROMPT_STAGE2 = Path(__file__).parent.parent.parent / "prompt" / "热点新闻_阶段2_汇总报告.md"
MAX_CONTENT_CHARS = 800
BATCH_SIZE = 6
MAX_RETRIES = 3
RETRY_DELAY = 3

# 模块级缓存，避免每批重新读磁盘
_TEMPLATE_STAGE1_CACHE: str | None = None
_TEMPLATE_STAGE2_CACHE: str | None = None


# ============ 模板加载（带缓存） ============


def _load_stage1_template() -> str:
    global _TEMPLATE_STAGE1_CACHE
    if _TEMPLATE_STAGE1_CACHE is None:
        _TEMPLATE_STAGE1_CACHE = PROMPT_STAGE1.read_text(encoding="utf-8") if PROMPT_STAGE1.exists() else ""
    return _TEMPLATE_STAGE1_CACHE


def _load_stage2_template() -> str:
    global _TEMPLATE_STAGE2_CACHE
    if _TEMPLATE_STAGE2_CACHE is None:
        _TEMPLATE_STAGE2_CACHE = PROMPT_STAGE2.read_text(encoding="utf-8") if PROMPT_STAGE2.exists() else ""
    return _TEMPLATE_STAGE2_CACHE


# ============ JSON 验证 ============


def _looks_like_json_array(text: str) -> bool:
    text = text.strip()
    text = re.sub(r'^```json\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'^```\s*', '', text)
    return text.startswith("[")


def _looks_like_json_object(text: str) -> bool:
    text = text.strip()
    text = re.sub(r'^```json\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'^```\s*', '', text)
    return text.startswith("{")


# ============ Stage 1 ============


def _build_news_item_text(item: dict) -> str:
    parts = [f"标题：{item['title']}"]
    parts.append(f"数据源：{item['source_name']}")
    if item.get("publish_time"):
        parts.append(f"发布时间：{item['publish_time']}")
    if item.get("summary"):
        parts.append(f"已有摘要：{item['summary']}")
    if item.get("related_sectors"):
        parts.append(f"关联板块：{item['related_sectors']}")
    if item.get("reason"):
        parts.append(f"入围原因：{item['reason']}")
    if item.get("intensity"):
        parts.append(f"强度：{item['intensity']}")
    if item.get("expected_change"):
        parts.append(f"预期变化：{item['expected_change']}")
    parts.append(f"重要性评分：{item['importance_score']}")
    return "\n".join(parts)


def _build_stage1_prompt(items: list[dict]) -> str:
    template = _load_stage1_template()
    blocks = []
    for i, item in enumerate(items):
        blocks.append(f"--- 新闻{i + 1} ---\n" + _build_news_item_text(item))
    return template.replace("<<news_items>>", "\n\n".join(blocks))


def _parse_stage1_response(text_blocks: list[str]) -> list[dict] | None:
    combined = "\n".join(text_blocks).strip()
    combined = re.sub(r'^```json\s*', '', combined, flags=re.IGNORECASE)
    combined = re.sub(r'^```\s*', '', combined).strip()
    m = re.search(r'\[[\s\S]*\]', combined)
    if not m:
        return None
    try:
        data = json.loads(m.group())
        return data if isinstance(data, list) else None
    except json.JSONDecodeError:
        return None


async def _stage1_batch(items: list[dict], timeout: int) -> list[dict]:
    prompt = _build_stage1_prompt(items)
    news_ids = [it["id"] for it in items]
    for attempt in range(1, MAX_RETRIES + 1):
        if attempt > 1:
            log(f"  Stage1 重试 {attempt}，news_ids={news_ids}")
        try:
            blocks = await call_async_raw(prompt, timeout=timeout)
            if not blocks:
                log(f"  Stage1 blocks 为空，news_ids={news_ids}")
                await asyncio.sleep(RETRY_DELAY)
                continue
            combined = "\n".join(blocks).strip()
            if not _looks_like_json_array(combined):
                log(f"  Stage1 返回不是 JSON 数组，news_ids={news_ids}，前200：{combined[:200]}")
                await asyncio.sleep(RETRY_DELAY)
                continue
            result = _parse_stage1_response(blocks)
            if result:
                return result
            log(f"  Stage1 解析失败，news_ids={news_ids}")
            await asyncio.sleep(RETRY_DELAY)
        except Exception as e:
            log(f"  Stage1 异常 {e}，news_ids={news_ids}")
            await asyncio.sleep(RETRY_DELAY)
    return []


# ============ Stage 2 ============


def _build_stage2_prompt(all_items: list[dict]) -> str:
    template = _load_stage2_template()
    blocks = []
    for i, item in enumerate(all_items):
        lines = [f"--- 摘要{i + 1} ---"]
        lines.append(f"标题：{item.get('title', '')}")
        lines.append(f"简要摘要：{item.get('brief_summary', '')}")
        lines.append(f"刺激源：{item.get('stimulus', '')}")
        if item.get("sectors"):
            lines.append(f"相关板块：{', '.join(item['sectors'])}")
        lines.append(f"显著性：{item.get('significance', '中')}")
        lines.append(f"预期变化：{item.get('expected_change', '')}")
        lines.append(f"入围原因：{item.get('reason', '')}")
        blocks.append("\n".join(lines))
    return template.replace("<<summary_items>>", "\n\n".join(blocks))


async def _stage2_aggregate(all_items: list[dict], timeout: int) -> dict | None:
    prompt = _build_stage2_prompt(all_items)
    for attempt in range(1, MAX_RETRIES + 1):
        if attempt > 1:
            log(f"  Stage2 重试 {attempt}")
        try:
            blocks = await call_async_raw(prompt, timeout=timeout)
            if not blocks:
                await asyncio.sleep(RETRY_DELAY)
                continue
            combined = "\n".join(blocks).strip()
            if not _looks_like_json_object(combined):
                log(f"  Stage2 返回不是 JSON 对象，前200：{combined[:200]}")
                await asyncio.sleep(RETRY_DELAY)
                continue
            result = parse_response(blocks)
            if result and isinstance(result, dict):
                return result
            log(f"  Stage2 解析失败")
            await asyncio.sleep(RETRY_DELAY)
        except Exception as e:
            log(f"  Stage2 异常 {e}")
            await asyncio.sleep(RETRY_DELAY)
    return None


# ============ 主流程（单一 asyncio.run，避免每批新建事件循环） ============


def _to_item_dict(r: tuple) -> dict:
    return {
        "id": r[0], "news_id": r[1], "source_name": r[2] or "",
        "title": r[3] or "", "url": r[4] or "", "publish_time": r[5] or "",
        "summary": r[6] or "", "related_sectors": r[7] or "",
        "importance_score": r[8] or 0, "reason": r[9] or "",
        "direction": r[10] or "", "intensity": r[11] or "",
        "expected_change": r[12] or "", "duration": r[13] or "",
        "expectation_level": r[14] or "", "market_mode": r[15] or "",
        "created_at": r[16] or "",
    }


async def _run_generate(date_str: str, min_score: int, limit: int, timeout: int) -> dict:
    records = get_positive_by_date(date_str, min_score=min_score, limit=limit)
    if not records:
        return {"error": f"{date_str} 无积极高分新闻"}

    all_items_raw = [_to_item_dict(r) for r in records if r[3]]
    if not all_items_raw:
        return {"error": "无有效标题的新闻"}

    batch_count = math.ceil(len(all_items_raw) / BATCH_SIZE)
    log(f"分 {batch_count} 批处理（每批 {BATCH_SIZE} 条）")

    all_items: list[dict] = []
    stage1_failed = 0

    for i in range(0, len(all_items_raw), BATCH_SIZE):
        batch = all_items_raw[i:i + BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        news_ids = [it["id"] for it in batch]
        log(f"  Stage1 批次 {batch_num}/{batch_count}，news_ids={news_ids}")
        items = await _stage1_batch(batch, timeout=timeout)
        if not items:
            stage1_failed += 1
            for it in batch:
                all_items.append({
                    "title": it["title"],
                    "brief_summary": it.get("summary", "")[:100] or it["title"],
                    "stimulus": "无法判断",
                    "sectors": [it["related_sectors"]] if it["related_sectors"] else [],
                    "significance": "中",
                    "expected_change": it.get("expected_change", ""),
                    "reason": it.get("reason", ""),
                })
        else:
            for item, orig in zip(items, batch):
                item["title"] = orig["title"]
                all_items.append(item)
            log(f"  Stage1 批次 {batch_num} 完成，获取 {len(items)} 条摘要")

    log(f"Stage1 完成：{len(all_items)} 条摘要，{stage1_failed} 批失败")

    log("Stage2 开始汇总...")
    final = await _stage2_aggregate(all_items, timeout=timeout)
    if not final:
        return {"error": "Stage2 汇总失败"}

    result = {
        "date": date_str,
        "total_news": len(all_items_raw),
        "summary": final.get("summary", ""),
        "main_stimulus": final.get("main_stimulus", ""),
        "sector_analysis": final.get("sector_analysis", ""),
        "market_outlook": final.get("market_outlook", ""),
        "insights": final.get("insights", ""),
    }
    save_summary(date_str, result, summary_type="热点新闻")
    return result


def generate_hot_news(date_str: str | None = None, min_score: int = 6, limit: int = 200, timeout: int = 120) -> dict:
    init_log()
    if not date_str:
        date_str = get_latest_importance_date()
        if not date_str:
            log("无最新新闻日期")
            return {"error": "无最新新闻日期"}
        log(f"自动取最新日期: {date_str}")

    log(f"=== 热点新闻生成开始 date={date_str}, min_score={min_score} ===")
    log(f"获取 importance 记录...")
    return asyncio.run(_run_generate(date_str, min_score, limit, timeout))
