"""
news_pipeline.py - 新闻采集评分完整流程服务

使用：
  python service/news_pipeline.py              # 完整流程
  python service/news_pipeline.py --step 2     # 从 Step 2 开始跑到最后
  python service/news_pipeline.py --only 4     # 仅跑 Step 4
  python service/news_pipeline.py --end 5      # 跑到 Step 5 结束（含）
"""
import argparse
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable

# 脚本直跑入口（python service/news_pipeline.py）时，需要先把 backend/ 加到 sys.path
# 才能 import script.bootstrap。被 schedule_service / run_scheduler 以模块方式 import 时
# 这个 insert 无副作用（重复路径会被 bootstrap 内的去重逻辑跳过）。
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from script.bootstrap import *  # 统一路径管理
from script.db import init_db
from script.log import log as _log
from script.common.datetimeutil import now_iso


def log(msg: str):
    _log("news_pipeline", msg)


# ---------------------------------------------------------------------------
# Step 数据描述（唯一信息源：序号 / 名称 / 说明 / 入口）
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Step:
    num: int
    name: str
    desc: str
    runner: Callable[[], None]


@contextmanager
def _isolated_argv():
    """临时清空 sys.argv，避免下游 main() 的 argparse 误吸 pipeline 自己的参数。"""
    saved = sys.argv
    sys.argv = [saved[0]] if saved else [""]
    try:
        yield
    finally:
        sys.argv = saved


def _run_async(coro_factory: Callable) -> None:
    """异步入口适配（统一一处 asyncio.run，避免重复）。"""
    import asyncio
    with _isolated_argv():
        asyncio.run(coro_factory())


def _run_sync(fn: Callable, *args, **kwargs) -> object:
    with _isolated_argv():
        return fn(*args, **kwargs)


# ---------------------------------------------------------------------------
# Step 入口（每个只做一件事：调用对应子模块。导入延迟到调用时，
# 让 --only/--step 跑部分流程时不被无关 step 的依赖拖累）
# ---------------------------------------------------------------------------

def _list_crawler() -> None:
    from script.crawl.list_crawler import main
    _run_async(main)


def _news_filter() -> None:
    from script.crawl.news_filter import main
    _run_async(main)


def _article_crawler() -> None:
    from script.crawl.article_crawler import main
    _run_async(main)


def _scorer() -> None:
    from script.score.scorer import main
    _run_sync(main)
    # scorer 结束时更新一次缓存
    _update_cache()


def _find_stocks() -> None:
    from script.stock.find_stocks_logic import findStocks
    _run_sync(findStocks, dry_run=False, min_score=6)


def _hot_news() -> None:
    from script.anomaly_news.hot_news import generate_hot_news
    _run_sync(generate_hot_news, min_score=6)
    _update_cache()


def _sync_sector_values() -> None:
    from script.sector.sync_sector_values import main
    _run_sync(main)


def _update_cache() -> None:
    from backend.api.news import update_news_cache
    result = _run_sync(update_news_cache)
    log(f"  latest={result['latest']}, history={result['history']}")


STEPS: tuple[Step, ...] = (
    Step(1, "list_crawler",       "采集新闻列表", _list_crawler),
    Step(2, "news_filter",        "LLM过滤",      _news_filter),
    Step(3, "article_crawler",    "采集文章正文", _article_crawler),
    Step(4, "scorer",             "LLM评分",      _scorer),
    Step(5, "findStocks",         "核心标的发现", _find_stocks),
    Step(6, "sync_sector_values", "同步板块指数", _sync_sector_values),
    Step(7, "update_cache",       "更新新闻缓存", _update_cache),
    Step(8, "hot_news",          "热点新闻简报", _hot_news),
)


# ---------------------------------------------------------------------------
# 统一执行：日志/计时/异常 boilerplate 只出现一次
# ---------------------------------------------------------------------------

def _execute(step: Step) -> None:
    start = datetime.now()
    log(f"=== Step {step.num}: {step.desc} [{now_iso()}] ===")
    try:
        step.runner()
    except Exception as e:
        log(f"Step {step.num} 失败: {e}")
        raise
    elapsed = (datetime.now() - start).total_seconds()
    log(f"Step {step.num} 完成，耗时 {elapsed:.1f} 秒")


def run_pipeline(start_step: int = 1, end_step: int | None = None) -> None:
    """
    执行流水线 [start_step, end_step] 区间（end_step=None 表示跑到最后）。

    Step 编号：1 list_crawler · 2 news_filter · 3 article_crawler ·
              4 scorer · 5 findStocks · 6 sync_sector_values · 7 update_cache · 8 hot_news
    """
    log("=" * 60)
    range_desc = f"Step {start_step}" + (f"-{end_step}" if end_step else "+")
    log(f"新闻采集评分流程开始 ({range_desc})")
    log("=" * 60)

    init_db()
    started = datetime.now()

    try:
        for step in STEPS:
            if step.num < start_step:
                log(f"[跳过] Step {step.num} {step.name}")
                continue
            if end_step is not None and step.num > end_step:
                break
            _execute(step)

        elapsed = (datetime.now() - started).total_seconds()
        log("=" * 60)
        log(f"流程结束，耗时 {elapsed:.1f} 秒")
        log("=" * 60)
    except Exception as e:
        log(f"流程异常中断: {e}")
        raise


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args() -> tuple[int, int | None]:
    parser = argparse.ArgumentParser(description="新闻采集评分流程")
    parser.add_argument("--step", type=int, default=1,
                        help=f"从第几步开始执行（1-{len(STEPS)}），默认 1")
    parser.add_argument("--only", type=int,
                        help="仅执行指定的一步（覆盖 --step / --end）")
    parser.add_argument("--end", type=int,
                        help=f"到第几步结束（1-{len(STEPS)}，含），默认到最后")
    args = parser.parse_args()
    if args.only is not None:
        return args.only, args.only
    return args.step, args.end


if __name__ == "__main__":
    start, end = _parse_args()
    run_pipeline(start_step=start, end_step=end)
