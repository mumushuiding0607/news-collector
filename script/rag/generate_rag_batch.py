"""
generate_rag_batch.py - 批量生成板块核心标的 RAG 报告

功能：
  - 一次传入多个板块（逗号分隔），并行调用 LLM 生成
  - 每个板块独立生成、独立入库，无交叉污染

使用：
  python script/rag/generate_rag_batch.py --sectors "房地产,建筑装饰,白酒"
  python script/rag/generate_rag_batch.py --sectors "半导体,AI视频" --save
"""

import argparse
import asyncio
import sys
import time
from pathlib import Path

_BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_BASE_DIR))
sys.path.insert(0, str(_BASE_DIR / "script"))

from llm import call_async_raw
from llm.prompts import get_rag_prompt
from rag.parser import save_to_db
from common.log import log as _ulog


def log(msg: str):
    _ulog("generate_rag_batch", msg)


async def _generate_one(sector: str, semaphore: asyncio.Semaphore, save_report: bool) -> dict:
    """单个板块的完整生成流程（async + semaphore 限流）"""
    async with semaphore:
        t0 = time.time()
        prompt = get_rag_prompt(sector)

        text_blocks = await call_async_raw(prompt, timeout=180)
        if not text_blocks:
            return {"sector": sector, "success": False, "error": "LLM 返回为空", "elapsed": time.time() - t0}

        report_text = "\n".join(text_blocks)

        if save_report:
            report_dir = _BASE_DIR / "rag_reports"
            report_dir.mkdir(exist_ok=True)
            filename = f"{sector}_{int(time.time())}.txt"
            (report_dir / filename).write_text(report_text, encoding="utf-8")

        ok = save_to_db(sector, report_text)
        elapsed = time.time() - t0

        return {
            "sector": sector,
            "success": ok,
            "elapsed": elapsed,
            "stocks_count": len([l for l in report_text.split('\n') if l.startswith('|') and '**' in l]) if ok else 0,
        }


async def _run_batch(sectors: list[str], concurrency: int = 3, save_report: bool = False) -> list[dict]:
    """并发执行所有板块，semaphore 控制并行数"""
    semaphore = asyncio.Semaphore(concurrency)

    log(f"启动批量生成，并发数={concurrency}，板块数={len(sectors)}")
    log("=" * 60)

    tasks = [_generate_one(s, semaphore, save_report) for s in sectors]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    processed = []
    for r in results:
        if isinstance(r, Exception):
            processed.append({"success": False, "error": str(r)})
        else:
            processed.append(r)

    return processed


def run(sectors: str, concurrency: int = 3, save_report: bool = False) -> list[dict]:
    """
    批量生成板块 RAG 报告并入库。

    Args:
        sectors: 逗号分隔的板块名，如 "房地产,建筑装饰"
        concurrency: 并行 LLM 调用数，默认 3，建议不超过 5
        save_report: 是否保存原始报告到文件
    """
    sector_list = [s.strip() for s in sectors.split(",") if s.strip()]
    if not sector_list:
        log("未提供有效板块")
        return []

    log(f"待处理板块: {sector_list}")
    log("=" * 60)

    t0 = time.time()
    results = asyncio.run(_run_batch(sector_list, concurrency=concurrency, save_report=save_report))
    total_elapsed = time.time() - t0

    log("=" * 60)
    log(f"批量完成，共 {len(sector_list)} 个板块，耗时 {total_elapsed:.1f}s")

    ok_list = [r for r in results if r.get("success")]
    fail_list = [r for r in results if not r.get("success")]

    for r in ok_list:
        log(f"  [OK]  {r['sector']}  ({r.get('elapsed', 0):.1f}s)")

    for r in fail_list:
        log(f"  [FAIL] {r['sector']}  {r.get('error', 'unknown error')}")

    log(f"成功 {len(ok_list)}/{len(sector_list)}")
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="批量生成板块核心标的 RAG 报告")
    parser.add_argument("--sectors", required=True, help="板块名称（逗号分隔）")
    parser.add_argument("--concurrency", type=int, default=3, help="并行调用数，默认3，建议不超过5")
    parser.add_argument("--save", action="store_true", help="保存原始报告到文件")
    args = parser.parse_args()

    run(args.sectors, concurrency=args.concurrency, save_report=args.save)