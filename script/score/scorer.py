"""
read_news.py - 新闻评分模块

优化备注（2026-05-30）：
  - LLM调用必须串行，禁止并发批量（token有限、速度有限、批量易失败）
  - scorer.py 不需要改并发逻辑，保持现状

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

from script.common.db import get_unread, mark_scored, insert_importance
from script.common.db.sectors import normalize
from llm import call
from common.log import log as _log


# ---------------------------------------------------------------------------
# 路径配置
# ---------------------------------------------------------------------------

DB_PATH = Path(__file__).resolve().parent.parent.parent / "db" / "primary.db"
SOURCES_CONFIG = Path(__file__).resolve().parent.parent.parent / "config" / "sources.json"
PROMPT_FILE = Path(__file__).resolve().parent.parent.parent / "prompt" / "事件评估.md"
LOG_DIR = Path(__file__).resolve().parent.parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / f"scoring_{datetime.now().strftime('%Y%m%d')}.log"


def log(msg: str):
    _log("scorer", msg)


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
    # 替换模板中的占位符
    prompt = template.replace("<<source_name>>", news.get('source_name', ''))
    prompt = prompt.replace("<<title>>", news.get('title', '') or '')
    prompt = prompt.replace("<<publish_time>>", news.get('publish_time', '') or '')
    prompt = prompt.replace("<<content>>", news.get('content', '')[:3000] or '')
    return prompt


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
    news_id, source_name, title, url, subtitle, publish_time, content, batch_id = news_row

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
        "batch_id": batch_id,
        "source_name": source_name,
        "title": title,
        "url": url,
        "publish_time": publish_time,
        "summary": result.get("summary", ""),
        "related_sectors": normalized_str,
        "importance_score": result.get("importance_score", 0),
        "reason": result.get("reason", ""),
        "direction": result.get("direction", ""),
        "intensity": result.get("intensity", 0),
        "expected_change": result.get("expected_change", ""),
        "duration": result.get("duration", ""),
        "expectation_level": result.get("expectation_level", ""),
        "market_mode": result.get("market_mode", ""),
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


def process_with_retry(news_row: tuple, dry_run: bool = False, max_retries: int = 3) -> dict | None:
    """
    处理单条新闻，带重试机制。
    如果 LLM 调用异常，立即停止并返回 None。
    """
    news_id = news_row[0]

    for attempt in range(max_retries):
        try:
            result = process_news(news_row, dry_run=dry_run)
            return result
        except Exception as e:
            log(f"  -> id={news_id} 异常: {type(e).__name__}: {e}")
            if attempt < max_retries - 1:
                import time
                time.sleep(2 ** attempt)  # 指数退避
                log(f"  -> id={news_id} 重试 {attempt + 2}/{max_retries}")
            else:
                log(f"  -> id={news_id} 重试耗尽，保持new状态")
                return None
    return None


def main():
    parser = argparse.ArgumentParser(description="新闻评分模块")
    parser.add_argument("--limit", type=int, default=5, help="每次循环处理的条数（默认5）")
    parser.add_argument("--dry-run", action="store_true", help="仅模拟，不写入数据库")
    parser.add_argument("--max-cycles", type=int, default=100, help="最大循环次数（默认100）")
    args = parser.parse_args()

    log("=" * 60)
    log(f"News scoring start {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"DB: {DB_PATH}")
    log(f"Mode: {'DRY-RUN' if args.dry_run else 'LIVE'}")
    log(f"每轮处理条数: {args.limit}")
    log("=" * 60)

    cycle = 0
    total_ok = 0
    total_skip = 0
    total_failed = 0

    while cycle < args.max_cycles:
        cycle += 1

        # 读取待处理新闻（status='read' 且 is_useful=1）
        all_news = get_unread(limit=args.limit)

        if not all_news:
            log(f"\n[循环 {cycle}] 没有待处理的新闻，退出。")
            break

        log(f"\n[循环 {cycle}/{args.max_cycles}] 待处理新闻: {len(all_news)} 条")

        for news_row in all_news:
            result = process_with_retry(news_row, dry_run=args.dry_run)

            news_id = news_row[0]

            if result is None:
                # LLM调用失败，停止执行
                log(f"\n!!! LLM调用异常，停止执行 !!!")
                log(f"请检查问题后重新运行 scorer.py")
                log("=" * 60)
                log(f"当前统计: 评分入库 {total_ok} 条, 跳过 {total_skip} 条, LLM失败 {total_failed} 条")
                log(f"总循环: {cycle}")
                return

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

    log("=" * 60)
    log(f"完成: 评分入库 {total_ok} 条, 跳过 {total_skip} 条, LLM失败 {total_failed} 条")
    log(f"总循环: {cycle}")


if __name__ == "__main__":
    main()