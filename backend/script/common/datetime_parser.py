"""
datetime_parser.py - 统一的日期时间解析模块

学习阶段：分析样本数据，推断日期格式，存入 list_config
抓取阶段：使用 list_config 中的格式信息，解析原始时间为统一格式

格式类型：
- unix: Unix 时间戳（秒），如 1781074167
- unix_ms: Unix 时间戳（毫秒），如 1781074167000
- iso: ISO 8601 格式，如 2026-06-10T12:01:00
- date: 日期格式如 2026-06-10
- datetime: 日期时间格式如 2026-06-10 12:01
- chinese: 中文格式如 06/10 12:01
- custom: 自定义格式，如 %Y-%m-%d %H:%M:%S
"""
from __future__ import annotations
import re
from datetime import datetime


# 常见日期格式模式
DATE_FORMATS = {
    "unix": ["unix", "timestamp", "time"],
    "unix_ms": ["unix_ms", "timestamp_ms", "time_ms"],
    "iso": ["iso", "iso8601", "rfc3339"],
    "chinese": ["chinese", "06/10 12:01", "%m/%d %H:%M"],
    "chinese_full": ["2026年06月10日", "%Y年%m月%d日"],
    "date": ["2026-06-10", "%Y-%m-%d"],
    "datetime": ["2026-06-10 12:01", "%Y-%m-%d %H:%M"],
    "datetime_sec": ["2026-06-10 12:01:01", "%Y-%m-%d %H:%M:%S"],
}


def parse_timestamp(value: int | float) -> str | None:
    """解析 Unix 时间戳，返回统一格式字符串"""
    try:
        # 判断是秒还是毫秒
        if value > 1e12:  # 毫秒级时间戳
            value = value / 1000
        dt = datetime.fromtimestamp(value)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, OSError):
        return None


def parse_iso(value: str) -> str | None:
    """解析 ISO 8601 格式"""
    try:
        # 尝试多种 ISO 变体
        for fmt in ["%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S"]:
            try:
                dt = datetime.strptime(value[:19], fmt[:len(value)])
                return dt.strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                continue
        return None
    except Exception:
        return None


def parse_chinese(value: str) -> str | None:
    """解析中文日期格式如 06/10 12:01"""
    try:
        # 匹配 MM/DD HH:MM 或 MM/DD HH:MM:SS
        m = re.match(r"(\d{1,2})/(\d{1,2})\s+(\d{1,2}):(\d{2})(?::(\d{2}))?", value)
        if m:
            month, day, hour, minute = int(m[1]), int(m[2]), int(m[3]), int(m[4])
            second = int(m[5]) if m[5] else 0
            year = datetime.now().year
            dt = datetime(year, month, day, hour, minute, second)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        return None
    except Exception:
        return None


def parse_date(value: str) -> str | None:
    """解析标准日期格式如 2026-06-10 或 2026-06-10 12:01"""
    try:
        for fmt in ["%Y-%m-%d", "%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S"]:
            try:
                dt = datetime.strptime(value[:len("2026-06-10 12:01:01")], fmt)
                return dt.strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                continue
        return None
    except Exception:
        return None


def parse_date_string(value: str, format_hint: str | None = None) -> str:
    """
    将原始日期字符串解析为统一格式 %Y-%m-%d %H:%M:%S

    Args:
        value: 原始日期值（可能是时间戳、数字字符串、或日期字符串）
        format_hint: 格式提示（来自 list_config 的 date_format）

    Returns:
        统一格式的日期字符串，如果解析失败返回空字符串
    """
    if not value:
        return ""

    # 如果是数值（时间戳）
    if isinstance(value, (int, float)):
        result = parse_timestamp(value)
        return result or str(value)

    # 字符串类型
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return ""

        # 先尝试数值解析（字符串形式的时间戳）
        try:
            numeric_val = float(value)
            if numeric_val > 1e12:
                numeric_val /= 1000  # 毫秒转秒
            result = parse_timestamp(numeric_val)
            if result:
                return result
        except (ValueError, TypeError):
            pass

        # 根据 format_hint 解析
        if format_hint == "unix":
            try:
                return parse_timestamp(float(value)) or value
            except (ValueError, TypeError):
                pass
        elif format_hint == "iso":
            result = parse_iso(value)
            if result:
                return result
        elif format_hint == "chinese":
            result = parse_chinese(value)
            if result:
                return result
        elif format_hint == "date" or format_hint == "datetime":
            result = parse_date(value)
            if result:
                return result

        # 尝试自动推断格式
        # 优先：ISO 格式
        result = parse_iso(value)
        if result:
            return result

        # 中文格式
        result = parse_chinese(value)
        if result:
            return result

        # 标准日期格式
        result = parse_date(value)
        if result:
            return result

        # 无法解析，返回原值
        return value

    return str(value)


def learn_date_format(sample_values: list) -> str:
    """
    从样本值学习日期格式

    Args:
        sample_values: 日期值列表（来自同一条数据的多个样本）

    Returns:
        格式字符串，如 "unix", "chinese", "iso", "%Y-%m-%d %H:%M:%S" 等
    """
    if not sample_values:
        return "unknown"

    # 统计各类格式的数量
    format_counts = {
        "unix": 0,
        "unix_ms": 0,
        "iso": 0,
        "chinese": 0,
        "date": 0,
        "datetime": 0,
    }

    for value in sample_values:
        if value is None:
            continue

        # 数值类型 = Unix 时间戳
        if isinstance(value, (int, float)):
            if value > 1e12:
                format_counts["unix_ms"] += 1
            else:
                format_counts["unix"] += 1
            continue

        value_str = str(value).strip()
        if not value_str:
            continue

        # Unix 时间戳（字符串形式）
        try:
            f = float(value_str)
            if f > 1e12:
                format_counts["unix_ms"] += 1
            else:
                format_counts["unix"] += 1
            continue
        except (ValueError, TypeError):
            pass

        # ISO 格式
        if "T" in value_str or "Z" in value_str:
            format_counts["iso"] += 1
            continue

        # 中文格式 MM/DD HH:MM
        if re.match(r"\d{1,2}/\d{1,2}\s+\d{1,2}:\d{2}", value_str):
            format_counts["chinese"] += 1
            continue

        # 标准日期格式
        if re.match(r"\d{4}-\d{2}-\d{2}", value_str):
            if " " in value_str:
                format_counts["datetime"] += 1
            else:
                format_counts["date"] += 1
            continue

    # 返回最常见的格式
    for fmt in ["unix", "unix_ms", "iso", "chinese", "datetime", "date"]:
        if format_counts[fmt] > 0:
            return fmt

    return "unknown"


if __name__ == "__main__":
    # 测试
    test_values = [
        1781074167,  # unix
        "1781074167",  # unix string
        "2026-06-10T12:01:00",  # iso
        "06/10 12:01",  # chinese
        "2026-06-10 12:01:01",  # datetime
    ]

    print("=== 日期解析测试 ===")
    for v in test_values:
        result = parse_date_string(v)
        print(f"  {repr(v)} -> {result}")

    print("\n=== 格式学习测试 ===")
    samples = [
        "06/10 12:01",
        "06/09 15:30",
        "06/08 09:00",
    ]
    fmt = learn_date_format(samples)
    print(f"  样本 {samples} -> 格式: {fmt}")