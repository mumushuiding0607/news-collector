"""
auto_sync_sectors_rag.py - 全量同步板块核心标的 RAG 报告

功能：
  - 从 db.sectors 查询所有板块，每3个一组串联调用 generate_rag_batch 生成核心标的
  - 每批内部 LLM 并发处理3个板块，批与批之间完全串行

日志：
  - 控制台 + 文件 双输出
  - 日志文件：logs/auto_sync_sectors_rag_YYYYMMDD_HHMMSS.log

使用：
  python service/auto_sync_sectors_rag.py
"""

import sys
from pathlib import Path
from datetime import datetime

_BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BASE_DIR / "script"))
sys.path.insert(0, str(_BASE_DIR))

from common.db.connection import get_conn
from common.log import log as _log


def log(msg: str):
    _log("auto_sync_sectors_rag", msg)


def get_all_sectors() -> list[str]:
    """从数据库查询所有板块名称（归约到 db 层）"""
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT DISTINCT name FROM sectors ORDER BY name"
        ).fetchall()
        return [r[0] for r in rows if r[0]]
    finally:
        conn.close()


def chunk_list(lst: list, size: int) -> list[list]:
    """把列表切成每组 size 个"""
    return [lst[i:i + size] for i in range(0, len(lst), size)]


def run():
    """
    主流程：
    1. 查询所有板块
    2. 每3个一组，串联调用 generate_rag_batch.run()
       - 每批内部 concurrency=3，LLM 并发处理3个板块
       - 批与批之间完全串行
    """
    log("=" * 60)
    log("开始全量同步板块核心标的 RAG")
    log("=" * 60)

    sectors = get_all_sectors()
    if not sectors:
        log("未找到任何板块，退出")
        return

    log(f"共找到 {len(sectors)} 个板块")

    batches = chunk_list(sectors, 3)
    log(f"分为 {len(batches)} 批，每批3个板块并行，批间完全串行")

    total_ok = 0
    total_fail = 0

    for i, batch in enumerate(batches, 1):
        batch_str = ",".join(batch)
        log(f"\n--- 批次 {i}/{len(batches)}: {batch_str} ---")

        # 串联调用，禁止并发
        from script.rag.generate_rag_batch import run as generate_run
        results = generate_run(sectors=batch_str, concurrency=3, save_report=False)

        ok = sum(1 for r in results if r.get("success"))
        fail = len(results) - ok
        total_ok += ok
        total_fail += fail

        for r in results:
            status = "OK" if r.get("success") else f"FAIL({r.get('error', 'unknown')})"
            elapsed = r.get("elapsed", 0)
            log(f"  [{status}] {r.get('sector')} ({elapsed:.1f}s)")

        log(f"批次 {i} 完成: {ok} 成功, {fail} 失败")

    log("\n" + "=" * 60)
    log(f"全部完成: {total_ok} 成功, {total_fail} 失败")
    log("=" * 60)


if __name__ == "__main__":
    run()