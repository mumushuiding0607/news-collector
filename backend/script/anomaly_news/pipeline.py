"""
anomaly_news/pipeline.py - 异动消息处理流程

消息流水线（--pipeline news）：
  Step 1: 采集异动消息入库
  Step 2: 采集文章正文
  Step 3: 确认数据源（写入 source_crawl_configs）
  Step 4: 生成异动简报

使用：
  python -m script.anomaly_news.pipeline --pipeline news    # 消息流水线
  python -m script.anomaly_news.pipeline --only 1          # 仅跑 Step 1
"""
import argparse
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable

# 支持 python -m script.anomaly_news.pipeline 直接运行
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from script.bootstrap import *  # noqa: F401 统一路径管理
from script.log import log as _log
from script.common.datetimeutil import now_iso


def log(msg: str):
    _log("anomaly_pipeline", msg)


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


def _run_sync(fn: Callable, *args, **kwargs) -> object:
    with _isolated_argv():
        return fn(*args, **kwargs)


# ---------------------------------------------------------------------------
# Step 入口
# ---------------------------------------------------------------------------

def _fetch_anomalies() -> None:
    """Step 1: 采集异动消息入库（从同花顺抓取两页）"""
    from script.anomaly_news.fetcher import discover_and_save
    urls = [
        'https://yuanchuang.10jqka.com.cn/mrnxgg_list/',
        'https://yuanchuang.10jqka.com.cn/mrnxgg_list/index_2.shtml',
    ]
    total_fetched = 0
    total_saved = 0
    for url in urls:
        result = _run_sync(discover_and_save, url)
        total_fetched += result.get('total_anomalies', 0)
        total_saved += result.get('saved', 0)
    log(f"  fetched={total_fetched}, saved={total_saved}")


def _generate_summary() -> None:
    """Step 4: 生成异动简报"""
    from script.anomaly_news.summary import generate
    result = _run_sync(generate)
    if "error" in result:
        log(f"  error: {result['error']}")
    else:
        log(f"  date={result.get('date')}, total_news={result.get('total_news')}")


def _confirm_sources() -> None:
    """Step 3: 确认数据源，直接写入 source_crawl_configs"""
    from script.anomaly_news.confirm import confirm_sources
    result = _run_sync(confirm_sources, dry_run=False)
    log(f"  total={result['total']}, unregistered={result['unregistered']}, confirmed={result['confirmed']}")


def _crawl_anomaly_contents() -> None:
    """Step 2: 采集异动消息正文"""
    from script.anomaly_news.fetcher import crawl_anomaly_contents
    stats = _run_sync(crawl_anomaly_contents)
    log(f"  ok={stats['ok']}, fail={stats['fail']}")


# ---------------------------------------------------------------------------
# 流水线定义
# ---------------------------------------------------------------------------

PIPELINE_NEWS: tuple[Step, ...] = (
    Step(1, "fetch_anomalies",    "采集异动消息", _fetch_anomalies),
    Step(2, "crawl_contents",    "采集文章正文", _crawl_anomaly_contents),
    Step(3, "confirm_sources",   "确认数据源",   _confirm_sources),
    Step(4, "generate_summary", "生成异动简报", _generate_summary),
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


def _run_pipeline(steps: tuple[Step, ...], name: str, start_step: int = 1, end_step: int | None = None) -> None:
    """执行指定流水线"""
    log("=" * 60)
    range_desc = f"Step {start_step}" + (f"-{end_step}" if end_step else "+")
    log(f"[{name}] {range_desc}")
    log("=" * 60)

    started = datetime.now()
    try:
        for step in steps:
            if step.num < start_step:
                log(f"[跳过] Step {step.num} {step.name}")
                continue
            if end_step is not None and step.num > end_step:
                break
            _execute(step)

        elapsed = (datetime.now() - started).total_seconds()
        log("=" * 60)
        log(f"[{name}] 结束，耗时 {elapsed:.1f} 秒")
        log("=" * 60)
    except Exception as e:
        log(f"[{name}] 异常中断: {e}")
        raise


def run_pipeline(pipeline: str = "news", start_step: int = 1, end_step: int | None = None) -> None:
    """
    执行流水线。

    Args:
        pipeline: "news"（仅消息流水线）
        start_step: 从第几步开始
        end_step: 执行到第几步结束
    """
    if pipeline == "news":
        _run_pipeline(PIPELINE_NEWS, "消息流水线", start_step, end_step)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args():
    parser = argparse.ArgumentParser(description="异动消息处理流程")
    parser.add_argument("--pipeline", choices=["news"], default="news",
                        help="选择流水线：news=消息流水线（默认 news）")
    parser.add_argument("--step", type=int, default=1,
                        help="从第几步开始执行（默认 1）")
    parser.add_argument("--only", type=int,
                        help="仅执行指定的一步（覆盖 --step / --end）")
    parser.add_argument("--end", type=int,
                        help="执行到第几步结束")
    args = parser.parse_args()

    start = args.only or args.step or 1
    end = args.only or args.end

    return args.pipeline, start, end


if __name__ == "__main__":
    pipeline, start, end = _parse_args()
    run_pipeline(pipeline=pipeline, start_step=start, end_step=end)
