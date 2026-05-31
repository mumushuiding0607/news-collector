"""
generate_rag.py - 生成板块核心标的 RAG 报告

功能：
  - 根据板块名称生成核心标的报告
  - 调用 LLM 生成并解析入库

使用：
  python script/rag/generate_rag.py --sector "建筑装饰"
  python script/rag/generate_rag.py --sector "房地产" --save
"""

import argparse
import asyncio
import sys
from pathlib import Path

_BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_BASE_DIR))
sys.path.insert(0, str(_BASE_DIR / "script"))

from llm import call_async_raw
from llm.prompts import get_rag_prompt
from rag.parser import save_to_db


def _log(msg: str):
    """带时间戳的日志输出"""
    from datetime import datetime
    ts = datetime.now().strftime("%H:%M:%S")
    try:
        print(f"[{ts}] {msg}", flush=True)
    except UnicodeEncodeError:
        # GBK terminal fallback
        safe = msg.encode("gbk", errors="replace").decode("gbk")
        print(f"[{ts}] {safe}", flush=True)


def generate_report(sector: str) -> str:
    """调用 LLM 生成板块核心标的报告。"""
    prompt = get_rag_prompt(sector)
    _log(f"正在调用 LLM 生成 {sector} 核心标的报告...")

    text_blocks = asyncio.run(call_async_raw(prompt, timeout=180))
    if not text_blocks:
        raise RuntimeError("LLM 返回为空")

    return "\n".join(text_blocks)


def run(sector: str, save_report: bool = False) -> str:
    """生成板块核心标的 RAG 报告并入库。"""
    _log("=" * 60)
    _log(f"开始生成 {sector} 核心标的 RAG")
    _log("=" * 60)

    report_text = generate_report(sector)

    if save_report:
        report_dir = _BASE_DIR / "rag_reports"
        report_dir.mkdir(exist_ok=True)
        from datetime import datetime
        filename = f"{sector}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        report_path = report_dir / filename
        report_path.write_text(report_text, encoding="utf-8")
        _log(f"原始报告已保存: {report_path}")

    _log("正在解析入库...")
    success = save_to_db(sector, report_text)

    if success:
        _log(f"[OK] {sector} 核心标的 RAG 生成并入库成功")
    else:
        _log(f"[FAIL] {sector} 入库失败")
        raise RuntimeError("入库失败")

    return report_text


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="生成板块核心标的 RAG 报告")
    parser.add_argument("--sector", required=True, help="板块名称")
    parser.add_argument("--save", action="store_true", help="保存原始报告到文件")
    args = parser.parse_args()

    run(args.sector, args.save)
