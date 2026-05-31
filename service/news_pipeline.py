"""
news_pipeline.py - 新闻采集评分完整流程服务

优化备注（2026-05-30）：
  - LLM调用必须串行，禁止并发批量
  - 本脚本是串行执行：列表采集 -> LLM过滤 -> 正文采集 -> LLM评分 -> 板块同步

使用：
  python service/news_pipeline.py
"""

import sys
from pathlib import Path
from datetime import datetime

_BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BASE_DIR / "script"))
sys.path.insert(0, str(_BASE_DIR))

from common import init_all, init_db


def log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def run_list_crawler():
    """Step 1: 采集新闻列表"""
    log("=== Step 1: 采集新闻列表 ===")
    try:
        import asyncio
        from script.crawl.list_crawler import main as run_list
        asyncio.run(run_list())
        log("Step 1 完成")
    except Exception as e:
        log(f"Step 1 失败: {e}")
        raise


def run_article_crawler():
    """Step 3: 采集文章正文"""
    log("=== Step 3: 采集文章正文 ===")
    try:
        import asyncio
        from script.crawl.article_crawler import main as run_article
        asyncio.run(run_article())
        log("Step 3 完成")
    except Exception as e:
        log(f"Step 3 失败: {e}")
        raise


def run_news_filter():
    """Step 2: LLM过滤（标题+摘要过滤无价值新闻，串行批次）"""
    log("=== Step 2: LLM过滤 ===")
    try:
        import asyncio
        from script.crawl.news_filter import main as run_filter
        asyncio.run(run_filter())
        log("Step 2 完成")
    except Exception as e:
        log(f"Step 2 失败: {e}")
        raise


def run_scorer():
    """Step 4: LLM评分（串行）"""
    log("=== Step 4: LLM评分 ===")
    try:
        from script.score.scorer import main as run_score
        run_score()
        log("Step 4 完成")
    except Exception as e:
        log(f"Step 4 失败: {e}")
        raise


def run_sync_sector_values():
    """Step 5: 同步板块指数值"""
    log("=== Step 5: 同步板块指数 ===")
    try:
        from script.sector.sync_sector_values import main as run_sync
        run_sync()
        log("Step 5 完成")
    except Exception as e:
        log(f"Step 5 失败: {e}")
        raise


def run_pipeline():
    """
    完整串行流程：
    1. list_crawler（采集新闻列表）
    2. news_filter（LLM过滤，标题+摘要淘汰无价值新闻）
    3. article_crawler（采集过滤后新闻的正文）
    4. scorer（LLM评分）
    5. sync_sector_values（同步板块指数）
    """
    log("=" * 60)
    log("新闻采集评分完整流程开始")
    log("=" * 60)

    init_db()

    start = datetime.now()

    try:
        run_list_crawler()
        run_news_filter()
        run_article_crawler()
        run_scorer()
        run_sync_sector_values()

        elapsed = (datetime.now() - start).total_seconds()
        log("=" * 60)
        log(f"完整流程结束，耗时 {elapsed:.1f} 秒")
        log("=" * 60)

        # 更新新闻缓存
        try:
            from backend.api.news import update_news_cache
            result = update_news_cache()
            log(f"缓存已更新: latest={result['latest']}, history={result['history']}")
        except Exception as e:
            log(f"缓存更新失败: {e}")

    except Exception as e:
        log(f"流程异常中断: {e}")
        raise


if __name__ == "__main__":
    run_pipeline()