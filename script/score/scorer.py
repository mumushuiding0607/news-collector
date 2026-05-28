"""
read_news.py - 新闻评分模块

读取 primary_sources 中 status='new' 的新闻，
用 LLM 判断是否会引起交易市场波动，
若能则生成摘要/关联板块（归一化）/评分，存入 importance 表，
并标记该新闻为已读。

同一时间段评分的新闻算同一批次。

评分框架来自 prompt/事件评估.md

使用：
  python read_news.py [--limit N] [--dry-run]
"""

import argparse
import json
from datetime import datetime
from pathlib import Path

from common.db import init_db, get_unread, mark_read, ensure_table, insert_importance
from common.db.sectors import normalize
from common.llm_client import call


# ---------------------------------------------------------------------------
# 路径配置
# ---------------------------------------------------------------------------

DB_PATH = Path(__file__).resolve().parent.parent / "db" / "primary.db"
SOURCES_CONFIG = Path(__file__).resolve().parent.parent / "config" / "sources.json"
PROMPT_FILE = Path(__file__).resolve().parent.parent / "prompt" / "事件评估.md"


# ---------------------------------------------------------------------------
# 提示词构建
# ---------------------------------------------------------------------------

def load_prompt_template() -> str:
    """加载提示词模板"""
    if PROMPT_FILE.exists():
        return PROMPT_FILE.read_text(encoding="utf-8")
    return ""


def build_prompt(news: dict) -> str:
    """构建评分提示词"""
    template = load_prompt_template()
    return template.replace("<<source_name>>", news.get("source_name", ""))\
                   .replace("<<title>>", news.get("title", ""))\
                   .replace("<<publish_time>>", news.get("publish_time", ""))\
                   .replace("<<content>>", news.get("content", "")[:3000])


# ---------------------------------------------------------------------------
# 板块归一化
# ---------------------------------------------------------------------------

def normalize_sectors(raw_sectors: str) -> list[dict]:
    """将LLM输出的原始板块串归一化为标准板块列表"""
    if not raw_sectors:
        return []
    return normalize(raw_sectors)


def format_normalized_sectors(sector_list: list[dict]) -> str:
    """将归一化后的板块列表格式化为字符串（存库用）"""
    if not sector_list:
        return ""
    return "|".join(s["name"] for s in sector_list if s.get("normalized"))


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def process_news(news_row: tuple, dry_run: bool = False) -> dict | None:
    news_id, source_name, title, url, subtitle, publish_time, content = news_row

    if not content or len(content.strip()) < 20:
        print(f"  [SKIP] id={news_id} content too short, marking as read")
        return {"skipped": True, "reason": "content_too_short"}

    print(f"  -> id={news_id} | {title[:50]}")

    prompt = build_prompt({
        "source_name": source_name,
        "title": title or "",
        "publish_time": publish_time or "",
        "content": content or "",
    })

    result = call(prompt)

    if result is None:
        print(f"  [WARN] id={news_id} LLM 返回异常，标记为已读不评分")
        return {"skipped": True, "reason": "llm_failed"}

    will_flunctuate = result.get("will_flunctuate", False)

    if will_flunctuate is False:
        print(f"  [SKIP] 不会引起市场波动，标记为已读")
        return {"skipped": True, "reason": "no_fluctuation"}

    # 归一化板块
    raw_sectors = result.get("related_sectors", "")
    normalized = normalize_sectors(raw_sectors)
    normalized_str = format_normalized_sectors(normalized)

    return {
        "skipped": False,
        "news_id": news_id,
        "source_name": source_name,
        "title": title,
        "url": url,
        "publish_time": publish_time,
        "summary": result.get("summary", ""),
        "related_sectors": normalized_str,
        "importance_score": result.get("importance_score", 0),
        "reason": result.get("reason", ""),
    }


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="新闻评分模块")
    parser.add_argument("--limit", type=int, default=10, help="每次最多处理多少条新闻（默认10）")
    parser.add_argument("--dry-run", action="store_true", help="仅模拟，不写入数据库")
    args = parser.parse_args()

    print("=" * 60)
    print(f"News scoring start {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"DB: {DB_PATH}")
    print(f"Mode: {'DRY-RUN' if args.dry_run else 'LIVE'}")
    print("=" * 60)

    init_db()
    ensure_table()

    try:
        cfg = json.loads(open(SOURCES_CONFIG, encoding="utf-8").read())
        batch_limit = cfg.get("scoringBatchSize", args.limit)
    except Exception:
        batch_limit = args.limit

    news_list = get_unread(limit=batch_limit)
    print(f"待处理新闻: {len(news_list)} 条")

    if not news_list:
        print("没有待处理的新闻，退出。")
        return

    total_ok = 0
    total_skip = 0

    for news_row in news_list:
        result = process_news(news_row, dry_run=args.dry_run)

        news_id = news_row[0]

        if result is None:
            continue

        if result["skipped"]:
            if not args.dry_run:
                mark_read(news_id)
            total_skip += 1
            reason = result.get("reason", "")
            print(f"  -> id={news_id} 已跳过({reason}) [OK]")
        else:
            if not args.dry_run:
                insert_importance(result)
                mark_read(news_id)
            total_ok += 1
            score = result.get("importance_score", 0)
            sectors = result.get("related_sectors", "")
            print(f"  -> id={news_id} 评分={score} 板块={sectors[:40]} [OK]")

        print()

    print("=" * 60)
    print(f"完成: 评分入库 {total_ok} 条, 跳过 {total_skip} 条")


if __name__ == "__main__":
    main()