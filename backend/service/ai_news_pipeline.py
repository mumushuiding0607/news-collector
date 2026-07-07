"""
ai_news_pipeline.py - AI 新闻采集评分完整流程服务

使用：
  python service/ai_news_pipeline.py              # 完整流程（默认 AI新闻）
  python service/ai_news_pipeline.py --type AI新闻
  python service/ai_news_pipeline.py --step 2     # 从 Step 2 开始
  python service/ai_news_pipeline.py --only 4     # 仅跑 Step 4
  python service/ai_news_pipeline.py --end 3      # 跑到 Step 3 结束
"""
import argparse
import os
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from script.bootstrap import *
from script.db import init_db
from script.log import log as _log
from script.common.datetimeutil import now_iso


def log(msg: str):
    _log("ai_news_pipeline", msg)


@dataclass(frozen=True)
class Step:
    num: int
    name: str
    desc: str
    runner: Callable[[], None]


@contextmanager
def _isolated_argv():
    saved = sys.argv
    sys.argv = [saved[0]] if saved else [""]
    try:
        yield
    finally:
        sys.argv = saved


def _run_async(coro_factory: Callable) -> None:
    import asyncio
    with _isolated_argv():
        asyncio.run(coro_factory())


def _run_sync(fn: Callable, *args, **kwargs) -> object:
    with _isolated_argv():
        return fn(*args, **kwargs)


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


def _update_cache() -> None:
    """保存 AI 新闻缓存到 backend/cache/（含正文内容）"""
    import json
    from script.bootstrap import CACHE_DIR
    from script.db import get_latest_ai_with_content, get_history_ai_with_content

    latest = get_latest_ai_with_content(limit=50)
    history = get_history_ai_with_content(limit=100)

    cache_dir = Path(CACHE_DIR)
    cache_dir.mkdir(parents=True, exist_ok=True)

    latest_path = cache_dir / "ai_news_latest.json"
    history_path = cache_dir / "ai_news_history.json"

    latest_path.write_text(json.dumps(latest, ensure_ascii=False, indent=2), encoding="utf-8")
    history_path.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")

    log(f"  缓存已更新: latest={len(latest)}条, history={len(history)}条")


STEPS: tuple[Step, ...] = (
    Step(1, "list_crawler",    "采集新闻列表", _list_crawler),
    Step(2, "news_filter",     "LLM过滤",      _news_filter),
    Step(3, "article_crawler", "采集文章正文", _article_crawler),
    Step(4, "scorer",         "LLM评分",      _scorer),
    Step(5, "update_cache",   "更新新闻缓存", _update_cache),
)


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
    log("=" * 60)
    range_desc = f"Step {start_step}" + (f"-{end_step}" if end_step else "+")
    log(f"AI新闻采集评分流程开始 ({range_desc})")
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


def _parse_args() -> tuple[int, int | None]:
    parser = argparse.ArgumentParser(description="AI新闻采集评分流程")
    parser.add_argument("--type", default="AI新闻",
                        help="新闻类型：股市新闻 或 AI新闻（默认 AI新闻）")
    parser.add_argument("--step", type=int, default=1,
                        help=f"从第几步开始执行（1-{len(STEPS)}），默认 1")
    parser.add_argument("--only", type=int,
                        help="仅执行指定的一步（覆盖 --step / --end）")
    parser.add_argument("--end", type=int,
                        help=f"到第几步结束（1-{len(STEPS)}，含），默认到最后")
    args = parser.parse_args()

    # 设置新闻类型（在 import 前）
    from script.bootstrap import set_news_type
    set_news_type(args.type)

    if args.only is not None:
        return args.only, args.only
    return args.step, args.end


if __name__ == "__main__":
    start, end = _parse_args()
    run_pipeline(start_step=start, end_step=end)
