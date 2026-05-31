"""
auto_match_sectors.py - 高分新闻自动关联板块

功能：
  - 查询 importance_score >= 8 且 related_sectors 为空的新闻
  - 查询所有板块名发给LLM让其匹配关联板块
  - 更新 importance.related_sectors

优化备注（2026-05-30）：
  - LLM调用必须串行，每次只处理一条新闻

使用：
  python script/rag/auto_match_sectors.py
"""

import sys
import asyncio
from pathlib import Path
from datetime import datetime

_BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_BASE_DIR))
sys.path.insert(0, str(_BASE_DIR / "script"))

from common.db.connection import get_conn
from common.db.rag import list_sectors as get_all_rag_sectors
from llm import call_async_raw
from common.log import timestamp_print as log


def get_high_score_no_sector_news():
    """获取高分但无板块的新闻"""
    conn = get_conn()
    try:
        rows = conn.execute("""
            SELECT id, title, summary, reason
            FROM importance
            WHERE importance_score >= 8
              AND (related_sectors IS NULL OR related_sectors = '')
            ORDER BY importance_score DESC
        """).fetchall()
        return [
            {"id": r[0], "title": r[1] or "", "summary": r[2] or "", "reason": r[3] or ""}
            for r in rows
        ]
    finally:
        conn.close()


def get_all_sector_names() -> list:
    """获取所有板块名（同花顺格式，有核心标的的板块优先）"""
    sectors = get_all_rag_sectors()
    return [s["name"] for s in sectors if s.get("stock_count", 0) > 0]


def call_llm_match_sectors(news: dict, sector_names: list) -> list:
    """
    调用LLM匹配关联板块（串行）。

    返回结果经过精确验证：先按|拆分LLM输出，再逐个验证是否在rag_sectors中存在。
    """
    prompt = f"""根据以下新闻，从给定列表中选择关联的板块（板块名必须完全匹配同花顺标准名称）。

新闻标题：{news['title']}
新闻摘要：{news['summary']}
推荐逻辑：{news['reason']}

可用板块列表：{', '.join(sector_names)}

请只输出关联的板块名，用|分隔（如：汽车制造|半导体），不要输出其他内容。如果不确定则输出空。"""

    blocks = asyncio.run(call_async_raw(prompt, timeout=60))
    if not blocks:
        return []

    combined = "\n".join(blocks).strip()
    raw_sectors = [s.strip() for s in combined.split("|") if s.strip()]

    # 精确验证：只在 rag_sectors 中存在的板块才保留
    sector_set = set(sector_names)
    matched = [s for s in raw_sectors if s in sector_set]

    return matched


def update_news_sectors(news_id: int, sectors: list) -> bool:
    """更新新闻的板块"""
    if not sectors:
        return False
    conn = get_conn()
    try:
        conn.execute("""
            UPDATE importance
            SET related_sectors = ?
            WHERE id = ?
        """, ("|".join(sectors), news_id))
        conn.commit()
        return True
    finally:
        conn.close()


def run():
    log("=" * 60)
    log("高分新闻自动关联板块")
    log("=" * 60)

    sector_names = get_all_sector_names()
    log(f"共有 {len(sector_names)} 个板块")

    news_list = get_high_score_no_sector_news()
    log(f"待处理新闻: {len(news_list)} 条")

    if not news_list:
        log("没有需要关联板块的新闻")
        return

    success = 0
    for i, news in enumerate(news_list, 1):
        log(f"[{i}/{len(news_list)}] {news['title'][:30]}...")
        matched = call_llm_match_sectors(news, sector_names)
        if matched:
            update_news_sectors(news["id"], matched)
            log(f"  -> {'|'.join(matched)}")
            success += 1
        else:
            log(f"  -> 未匹配")

    log(f"完成，成功 {success}/{len(news_list)} 条")


if __name__ == "__main__":
    run()
