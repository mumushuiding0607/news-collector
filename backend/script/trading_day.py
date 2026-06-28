"""
trading_day.py - 交易日计算模块

计算股票新闻发布后相对于今天的交易日年龄（跳过周末）。
"""

from datetime import datetime, timedelta


def get_trading_day_age(created_at: str, today: str) -> int:
    """
    计算今天相对于新闻创建日是第几个交易日（跳过周末）。

    Args:
        created_at: 新闻创建日期，格式 YYYY-MM-DD
        today: 今天日期，格式 YYYY-MM-DD

    Returns:
        0 → d1 (发布日)
        1 → d2 (发布后第1个交易日)
        2 → d3 (发布后第2个交易日)
        -1 → 不需要更新（超过2个交易日）
    """
    created = datetime.strptime(created_at, '%Y-%m-%d')
    today_dt = datetime.strptime(today, '%Y-%m-%d')

    if today_dt < created:
        return -1

    age = 0
    current = created + timedelta(days=1)  # 从创建日的下一天开始

    while current <= today_dt:
        if current.weekday() < 5:  # Mon-Fri (0-4)
            age += 1
        current += timedelta(days=1)

    if age > 2:
        return -1
    return age


def get_trading_day_name(age: int) -> str | None:
    """
    根据交易日年龄返回字段名。

    Args:
        age: 交易日年龄 (0/1/2)

    Returns:
        'd1', 'd2', 'd3' 或 None
    """
    if age == 0:
        return 'd1'
    elif age == 1:
        return 'd2'
    elif age == 2:
        return 'd3'
    return None