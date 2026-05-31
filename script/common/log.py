"""
log.py - 统一日志模块

所有程序日志必须引用此模块：
    from common.log import log

日志输出到 logs/YYYY-MM-DD/<module>.log，按日期分目录。
同一模块同一日期的日志追加写入。
"""

import sys
from pathlib import Path
from datetime import datetime

_BASE_DIR = Path(__file__).resolve().parent.parent.parent
_LOG_DIR = _BASE_DIR / "logs"


def _get_log_file(module: str) -> Path:
    today = datetime.now().strftime("%Y-%m-%d")
    day_dir = _LOG_DIR / today
    day_dir.mkdir(parents=True, exist_ok=True)
    return day_dir / f"{module}.log"


def log(module: str, msg: str):
    """
    统一日志接口。

    Args:
        module: 模块名称（建议用调用文件的简短标识，如 list_crawler、scorer）
        msg: 日志内容
    """
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"{ts}  [{module}]  {msg}"

    # 控制台
    try:
        print(line, flush=True)
    except UnicodeEncodeError:
        safe = line.encode("gbk", errors="replace").decode("gbk")
        print(safe, flush=True)

    # 写入当日日志文件
    log_file = _get_log_file(module)
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass  # 日志写入失败不影响主流程