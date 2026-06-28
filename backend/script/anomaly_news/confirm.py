"""
anomaly_news/confirm.py - 确认异动消息中的数据源

从 anomaly_news 提取未入库的数据源，用 LLM 确认网址，直接存入 source_crawl_configs。
"""
from script.log import log as _log, init_log
from script.db.anomaly_news import get_anomaly_news, mark_processed
from script.db.sources_db import upsert_crawl_config, get_crawl_config_by_name
from script.llm import call_async_raw


def log(msg: str):
    _log("confirm_anomaly", msg)


PROMPT_FILE = None  # 由调用方注入


def build_prompt(source_names: list[str]) -> str:
    """构建 LLM 提示词"""
    from pathlib import Path
    prompt_file = PROMPT_FILE or Path(__file__).parent.parent.parent / "prompt" / "数据源确认.md"
    template = prompt_file.read_text(encoding="utf-8") if prompt_file.exists() else ""
    names_text = "\n".join(f"- {name}" for name in source_names)
    return template.replace("<<source_names>>", names_text)


def parse_llm_response(text: str) -> list[dict]:
    """从 LLM 输出解析 JSON 数组"""
    import json
    import re

    m = re.search(r'\[[\s\S]*\]', text)
    if not m:
        return []
    try:
        data = json.loads(m.group())
        if not isinstance(data, list):
            return []
        result = []
        for item in data:
            if not isinstance(item, dict) or 'source_name' not in item or 'url' not in item:
                continue
            result.append({
                'source_name': item['source_name'],
                'url': item['url'],
            })
        return result
    except (json.JSONDecodeError, KeyError):
        return []


def confirm_sources(dry_run: bool = False) -> dict:
    """
    确认异动消息中未入库的数据源网址，直接写入 source_crawl_configs。

    Returns:
        {"total", "unregistered", "confirmed", "results"}
    """
    init_log()
    log("=" * 60)
    log(f"confirm_sources start (mode: {'DRY-RUN' if dry_run else 'LIVE'})")
    log("=" * 60)

    # 从 anomaly_news 获取不重复的未处理数据源
    records = get_anomaly_news(limit=1000, processed=0)
    if not records:
        log("无未处理的异动消息")
        return {"total": 0, "unregistered": 0, "confirmed": 0, "results": []}

    # 按 source_name 分组并清洗
    source_names_seen = {}
    for r in records:
        title = r[1] or ""
        raw_name = r[4]  # source_name 列
        if not raw_name:
            continue
        # 清洗：去除标题残留（如 "显示，英伟达..." → "显示"）
        name = raw_name.split('，')[0].split('：')[0].split('，')[0].strip()
        # 跳过已知乱码模式和无效长度
        if name in ('未知', '�') or len(name) < 2:
            # fallback：从标题逆推数据源
            from script.discovery.source_discovery import extract_source_name
            name = extract_source_name(title)
            if not name or len(name) < 2:
                continue
        if len(name) > 20:
            continue
        if name not in source_names_seen:
            source_names_seen[name] = r[0]

    unique_sources = list(source_names_seen.keys())
    log(f"发现未处理的数据源: {len(unique_sources)} 个")

    # 查询已入库的数据源（source_crawl_configs）
    existing_sources: set[str] = set()
    for name in unique_sources:
        cfg = get_crawl_config_by_name(name)
        if cfg is not None:
            existing_sources.add(name)

    unregistered = [s for s in unique_sources if s not in existing_sources]
    log(f"已入库: {len(existing_sources)} 个，未入库: {len(unregistered)} 个")

    if not unregistered:
        log("所有数据源已入库")
        if not dry_run:
            for r in records:
                mark_processed(r[0])
        return {"total": len(unique_sources), "unregistered": 0, "confirmed": 0, "results": []}

    log(f"待确认数据源: {unregistered}")

    # 调用 LLM 确认网址
    import asyncio
    try:
        prompt = build_prompt(unregistered)
        log(f"build_prompt 完成，长度={len(prompt)}")
        text_blocks = asyncio.run(call_async_raw(prompt, timeout=300))
        log(f"call_async_raw 返回，blocks={'有' if text_blocks else '无'}")
    except Exception as e:
        import traceback
        log(f"LLM 调用异常: {e}")
        log(traceback.format_exc())
        return {"total": len(unique_sources), "unregistered": len(unregistered), "confirmed": 0, "results": []}

    if not text_blocks:
        log("LLM 调用失败")
        return {"total": len(unique_sources), "unregistered": len(unregistered), "confirmed": 0, "results": []}

    report_text = "\n".join(text_blocks)
    results = parse_llm_response(report_text)
    log(f"LLM 确认了 {len(results)} 个数据源")

    # URL 标准化并过滤
    from script.common.urlutil import normalize_url
    valid_results = []
    for r in results:
        if r.get("url"):
            r["url"] = normalize_url(r["url"])
            valid_results.append(r)

    if not dry_run:
        saved = 0
        for r in valid_results:
            upsert_crawl_config(url=r["url"], name=r["source_name"], checked=0)
            saved += 1
        log(f"已保存 {saved} 条到 source_crawl_configs")
        # 标记 anomaly_news 为已处理
        for r in records:
            mark_processed(r[0])
        log(f"已标记 {len(records)} 条异动消息为已处理")
    else:
        saved = 0
        log(f"[DRY-RUN] 跳过保存，共 {len(valid_results)} 条待确认")

    return {
        "total": len(unique_sources),
        "unregistered": len(unregistered),
        "confirmed": saved,
        "results": valid_results,
    }
