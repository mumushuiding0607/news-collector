"""
log_service.py - 日志管理业务服务

处理日志文件的读取和管理：
- logs 目录下所有日志文件的列表
- 按日期分组
- 读取指定日志文件内容
- 支持分页读取大文件
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_LOGS_DIR = _PROJECT_ROOT / "logs"


def _ensure_dir():
    """确保 logs 目录存在"""
    if not _LOGS_DIR.exists():
        return []


def list_log_dates() -> list[str]:
    """获取所有日志日期目录（按日期倒序）"""
    if not _LOGS_DIR.exists():
        return []
    dates = [d.name for d in _LOGS_DIR.iterdir() if d.is_dir()]
    dates.sort(reverse=True)
    return dates


def list_log_files(date: str | None = None) -> list[dict]:
    """
    获取日志文件列表
    - date: 可选，筛选指定日期的目录
    - 返回文件信息列表，包含：path, name, size, modified
    """
    if not _LOGS_DIR.exists():
        return []

    result = []
    if date:
        target_dir = _LOGS_DIR / date
        if target_dir.exists():
            dirs = [target_dir]
        else:
            return []
    else:
        dirs = [d for d in _LOGS_DIR.iterdir() if d.is_dir()]

    for d in dirs:
        for f in d.iterdir():
            if f.is_file() and f.suffix in (".log", ".txt", ""):
                stat = f.stat()
                result.append({
                    "date": d.name,
                    "name": f.name,
                    "path": str(f.relative_to(_PROJECT_ROOT)),
                    "size": stat.st_size,
                    "size_display": _format_size(stat.st_size),
                    "modified": _format_time(stat.st_mtime),
                })

    # 排序：日期倒序，文件名正序
    result.sort(key=lambda x: (x["date"], x["name"]), reverse=True)
    return result


def read_log_content(path: str, offset: int = 0, limit: int = 500) -> dict:
    """
    读取日志文件内容（从末尾向前读取，即最新内容在前）
    - path: 日志文件路径（相对于项目根目录）
    - offset: 行偏移量
    - limit: 最大返回行数
    返回：{ lines: [], total_lines: int, has_more: bool, path: str }
    """
    full_path = _PROJECT_ROOT / path
    if not full_path.exists():
        raise FileNotFoundError(f"日志文件不存在: {path}")

    # 读取所有行
    lines = full_path.read_text(encoding="utf-8", errors="replace").splitlines()
    total_lines = len(lines)

    # 从末尾向前取
    start = max(0, total_lines - offset - limit)
    end = total_lines - offset
    selected = lines[start:end]

    # 反转，使最新内容在前
    selected.reverse()

    return {
        "lines": selected,
        "total_lines": total_lines,
        "offset": offset,
        "limit": limit,
        "has_more": offset + limit < total_lines,
        "path": path,
    }


def stream_log_tail(path: str, lines: int = 100) -> str:
    """
    读取日志文件最后 N 行（用于实时查看）
    返回字符串内容
    """
    full_path = _PROJECT_ROOT / path
    if not full_path.exists():
        raise FileNotFoundError(f"日志文件不存在: {path}")

    with open(full_path, "rb") as f:
        f.seek(0, 2)
        file_size = f.tell()
        if file_size == 0:
            return ""

        position = file_size
        line_count = 0
        while position > 0 and line_count < lines:
            read_size = min(8192, position)
            position -= read_size
            f.seek(position)
            chunk = f.read(read_size)
            line_count += chunk.count(b"\n")

        # 定位到起始位置
        if position > 0:
            f.seek(position)
        else:
            f.seek(0)

        # 跳过多余行
        remaining = line_count - lines
        if remaining > 0:
            for _ in range(remaining):
                f.readline()

        # 读取目标行
        result_lines = []
        for line in f:
            result_lines.append(line.decode("utf-8", errors="replace"))

        return "".join(result_lines)


def _format_size(size: int) -> str:
    """格式化文件大小"""
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f}{unit}"
        size /= 1024
    return f"{size:.1f}TB"


def _format_time(timestamp: float) -> str:
    """格式化时间戳"""
    import datetime
    return datetime.datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")