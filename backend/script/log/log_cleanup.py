"""
log_cleanup.py - 日志清理

定时删除 7 天前的日志目录，仅保留最近 7 天日志。
"""

from __future__ import annotations

import datetime
import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_LOGS_DIR = _PROJECT_ROOT / "logs"


def cleanup_old_logs(days: int = 7) -> dict:
    """
    删除指定天数之前的日志目录（保留最近 days 天）。
    返回被删除的目录列表和数量。
    """
    if not _LOGS_DIR.exists():
        logger.info("[LogCleanup] logs 目录不存在，无需清理")
        return {"deleted": [], "count": 0}

    cutoff = datetime.date.today() - datetime.timedelta(days=days)
    deleted = []

    for entry in _LOGS_DIR.iterdir():
        if not entry.is_dir():
            continue
        try:
            dir_date = datetime.datetime.strptime(entry.name, "%Y-%m-%d").date()
        except ValueError:
            # 非日期格式目录，跳过
            logger.warning(f"[LogCleanup] 跳过非日期目录: {entry.name}")
            continue

        if dir_date < cutoff:
            try:
                shutil.rmtree(entry)
                logger.info(f"[LogCleanup] 已删除日志目录: {entry.name}")
                deleted.append(entry.name)
            except Exception as e:
                logger.error(f"[LogCleanup] 删除失败 {entry.name}: {e}")
                continue

    logger.info(f"[LogCleanup] 清理完成，共删除 {len(deleted)} 个目录")
    return {"deleted": deleted, "count": len(deleted)}