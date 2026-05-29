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
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

from common.db import init_db, get_unread, mark_scored, ensure_table, insert_importance
from common.db.sectors import normalize
from common.llm_client import call


# ---------------------------------------------------------------------------
# 路径配置
# ---------------------------------------------------------------------------

DB_PATH = Path(__file__).resolve().parent.parent.parent / "db" / "primary.db"
SOURCES_CONFIG = Path(__file__).resolve().parent.parent / "config" / "sources.json"
PROMPT_FILE = Path(__file__).resolve().parent.parent / "prompt" / "事件评估.md"
LOG_DIR = Path(__file__).resolve().parent.parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / f"scoring_{datetime.now().strftime('%Y%m%d')}.log"


def log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


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
    # 将新闻格式化为模板期望的列表格式
    news_text = f"""{news.get('source_name', '')}
标题：{news.get('title', '')}
时间：{news.get('publish_time', '')}
正文：{news.get('content', '')[:3000]}"""
    return template.replace("<<news_list>>", news_text)


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
        log(f"  [SKIP] id={news_id} content too short, marking as read")
        return {"skipped": True, "reason": "content_too_short"}

    log(f"  -> id={news_id} | {title[:50]}")

    prompt = build_prompt({
        "source_name": source_name,
        "title": title or "",
        "publish_time": publish_time or "",
        "content": content or "",
    })

    result = call(prompt)

    if result is None or not isinstance(result, dict):
        log(f"  [WARN] id={news_id} LLM 返回异常（{type(result).__name__}），标记为已读不评分")
        return {"skipped": True, "reason": "llm_failed"}

    will_flunctuate = result.get("will_flunctuate", False)

    if will_flunctuate is False:
        log(f"  [SKIP] 不会引起市场波动，标记为已读")
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

def calc_batch_size(news_list: list[tuple], max_tokens_per_item: int = 500) -> int:
    """
    根据新闻内容总长度动态计算批次大小。

    每次请求的 prompt 包含模板(~500字符) + 新闻内容(3000字符/条)。
    LLM max_tokens=2000，输出 JSON 约需 200-300 字符。
    输入可用的 token 约 3000-5000（取决于模型上下文窗口）。

    估算公式：单条新闻约 3500 字符 -> 约 1000-1500 tokens
    保守估计每条新闻消耗 1500 tokens，4000 tokens 约可处理 2-3 条长新闻。
    """
    total_chars = sum(len(row[6] or "") for row in news_list)
    avg_chars_per_item = total_chars / len(news_list) if news_list else 3500

    # 估算每条新闻需要的 token（1 token ≈ 4 字符）
    estimated_tokens_per_item = avg_chars_per_item / 4 + 200  # +200 是模板开销

    # 预留 500 tokens 给模板和输出，实际输入上限约 3500 tokens
    available_tokens = 3500

    batch_size = max(1, int(available_tokens / estimated_tokens_per_item))
    return min(batch_size, 10)  # 上限10条


def main():
    parser = argparse.ArgumentParser(description="新闻评分模块")
    parser.add_argument("--limit", type=int, default=0, help="手动指定每次处理条数（0=自动计算）")
    parser.add_argument("--dry-run", action="store_true", help="仅模拟，不写入数据库")
    args = parser.parse_args()

    log("=" * 60)
    log(f"News scoring start {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"DB: {DB_PATH}")
    log(f"Mode: {'DRY-RUN' if args.dry_run else 'LIVE'}")
    log("=" * 60)

    init_db()
    ensure_table()

    # 一次读取所有待处理新闻（避免分批查询破坏顺序）
    all_news = get_unread(limit=100)  # 最多一 次读100条
    log(f"待处理新闻: {len(all_news)} 条")

    if not all_news:
        log("没有待处理的新闻，退出。")
        return

    # 根据内容总长度计算批次大小
    if args.limit > 0:
        batch_size = args.limit
    else:
        batch_size = calc_batch_size(all_news)

    log(f"动态批次大小: {batch_size} 条/批")

    total_ok = 0
    total_skip = 0
    processed = 0

    while processed < len(all_news):
        batch = all_news[processed:processed + batch_size]
        log(f"\n--- 批次: 起始id={batch[0][0]}, 数量={len(batch)} ---")

        for news_row in batch:
            result = process_news(news_row, dry_run=args.dry_run)

            news_id = news_row[0]

            if result is None:
                continue

            if result["skipped"]:
                if not args.dry_run:
                    mark_scored(news_id)
                total_skip += 1
                reason = result.get("reason", "")
                log(f"  -> id={news_id} 已跳过({reason}) [OK]")
            else:
                if not args.dry_run:
                    insert_importance(result)
                    mark_scored(news_id)
                total_ok += 1
                score = result.get("importance_score", 0)
                sectors = result.get("related_sectors", "")
                log(f"  -> id={news_id} 评分={score} 板块={sectors[:40]} [OK]")

            import time
            time.sleep(0.5)  # 避免API限流

        processed += len(batch)

    log("=" * 60)
    log(f"完成: 评分入库 {total_ok} 条, 跳过 {total_skip} 条")


if __name__ == "__main__":
    main()