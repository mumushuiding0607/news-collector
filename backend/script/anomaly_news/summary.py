"""
anomaly_news/summary.py - 异动简报生成（两阶段方案）

Stage 1: 每批新闻 → 生成结构化分篇摘要
Stage 2: 汇总所有分篇摘要 → 生成最终简报
"""
import asyncio
import json
import math
import re
from pathlib import Path

from script.log import log as _log, init_log
from script.db.anomaly_news import get_anomaly_news_by_date_with_content, get_latest_anomaly_date
from script.db.anomaly_summary_db import save_summary
from script.llm.client import call_async_raw, parse_response


def log(msg: str):
    _log("anomaly_summary", msg)


PROMPT_STAGE1 = Path(__file__).parent.parent.parent / "prompt" / "异动简报_阶段1_分篇摘要.md"
PROMPT_STAGE2 = Path(__file__).parent.parent.parent / "prompt" / "异动简报_阶段2_汇总报告.md"
MAX_CONTENT_CHARS = 800
BATCH_SIZE = 6
MAX_RETRIES = 3
RETRY_DELAY = 3

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


def _build_news_item_text(news: dict) -> str:
    parts = [f"标题：{news['title']}"]
    parts.append(f"数据源：{news['source_name']}")
    if news.get("publish_time"):
        parts.append(f"发布时间：{news['publish_time']}")
    content = news.get("content", "")
    if content:
        content = content[:MAX_CONTENT_CHARS]
        parts.append(f"正文：{content}")
    return "\n".join(parts)


def _build_stage1_prompt(news_list: list[dict]) -> str:
    template = _load_stage1_template()
    blocks = []
    for i, news in enumerate(news_list):
        blocks.append(f"--- 新闻{i + 1} ---\n" + _build_news_item_text(news))
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


async def _stage1_batch(news_list: list[dict], timeout: int) -> list[dict]:
    prompt = _build_stage1_prompt(news_list)
    news_ids = [n["id"] for n in news_list]
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
        if item.get("stocks"):
            lines.append(f"关联个股：{', '.join(item['stocks'])}")
        lines.append(f"市场显著性：{item.get('significance', '中')}")
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


# ============ 主流程 ============


def _to_news_dict(r: tuple) -> dict:
    return {
        "id": r[0], "title": r[1] or "", "url": r[2] or "",
        "publish_time": r[3] or "", "source_name": r[4] or "",
        "content": r[5] or "",
    }


async def _run_generate(date_str: str, limit: int, timeout: int) -> dict:
    records = get_anomaly_news_by_date_with_content(date_str, limit=limit)
    all_news = [_to_news_dict(r) for r in records if r[1]]
    if not all_news:
        return {"error": "无有效新闻"}

    batch_count = math.ceil(len(all_news) / BATCH_SIZE)
    log(f"分 {batch_count} 批处理（每批 {BATCH_SIZE} 条）")

    all_items: list[dict] = []
    stage1_failed = 0

    for i in range(0, len(all_news), BATCH_SIZE):
        batch = all_news[i:i + BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        news_ids = [n["id"] for n in batch]
        log(f"  Stage1 批次 {batch_num}/{batch_count}，news_ids={news_ids}")
        items = await _stage1_batch(batch, timeout=timeout)
        if not items:
            stage1_failed += 1
            for n in batch:
                all_items.append({
                    "title": n["title"],
                    "brief_summary": n.get("content", "")[:100] or n["title"],
                    "stimulus": "无法判断",
                    "sectors": [],
                    "stocks": [],
                    "significance": "低",
                })
        else:
            for item, news in zip(items, batch):
                item["title"] = news["title"]
                all_items.append(item)
            log(f"  Stage1 批次 {batch_num} 完成，获取 {len(items)} 条摘要")

    log(f"Stage1 完成：{len(all_items)} 条摘要，{stage1_failed} 批失败")

    log("Stage2 开始汇总...")
    final = await _stage2_aggregate(all_items, timeout=timeout)
    if not final:
        return {"error": "Stage2 汇总失败"}

    result = {
        "date": date_str,
        "total_news": len(all_news),
        "summary": final.get("summary", ""),
        "main_stimulus": final.get("main_stimulus", ""),
        "correlation": final.get("correlation", ""),
        "insights": final.get("insights", ""),
    }
    save_summary(date_str, result)
    return result


def generate(date_str: str | None = None, limit: int = 200, timeout: int = 120) -> dict:
    init_log()
    if not date_str:
        date_str = get_latest_anomaly_date()
        if not date_str:
            return {"error": "无异动消息数据"}

    log(f"=== 两阶段简报生成开始 date={date_str} ===")
    log(f"获取异动消息...")
    return asyncio.run(_run_generate(date_str, limit, timeout))
