"""
get_publish_sector_values.py - 获取新闻发布时的板块指数快照

功能：
  - 查询最新批次中得分最高的前 N 条新闻的 publish_sector_values
  - 按交易时段（盘前/盘中盘后）和日期合并查询，减少 API 调用
  - 批量查询同花顺获取板块指数

使用：
  python script/sector/get_publish_sector_values.py
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

# 添加 script 目录到 path
_BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BASE_DIR))

from api_clients.iwencai import query_wencai
from common.db.sectors import normalize
from common.db import importance as db_importance

# 从 sources.json 读取配置
CONFIG_PATH = _BASE_DIR.parent / "config" / "sources.json"

def load_config() -> dict:
    """加载 sources.json 配置"""
    import json
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def get_default_top_n() -> int:
    """获取默认的 top_n 值"""
    config = load_config()
    return config.get("top_n", 10)


def parse_period(date_str: str) -> str:
    """
    判断交易时段

    Args:
        date_str: 格式 YYYY-MM-DD HH:MM:SS

    Returns:
        "pre_market" 盘前 (00:01-09:30)
        "regular"    盘中/盘后 (09:30-23:59)
    """
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        hour = dt.hour
        minute = dt.minute

        # 盘前: 00:01 - 09:30
        if hour < 9 or (hour == 9 and minute <= 30):
            return "pre_market"
        # 盘中/盘后: 09:30 - 23:59
        else:
            return "regular"
    except ValueError:
        return "regular"


def get_query_date(news_date_str: str, period: str) -> str:
    """
    获取查询日期

    Args:
        news_date_str: 新闻发布日期 (YYYY-MM-DD HH:MM:SS)
        period: "pre_market" 或 "regular"

    Returns:
        查询日期 (YYYY-MM-DD)
    """
    try:
        news_date = datetime.strptime(news_date_str.split()[0], "%Y-%m-%d")
        if period == "pre_market":
            # 盘前查上一日收盘价
            return (news_date - timedelta(days=1)).strftime("%Y-%m-%d")
        else:
            # 盘中/盘后查当天收盘价
            return news_date.strftime("%Y-%m-%d")
    except ValueError:
        return news_date_str.split()[0]


def fetch_sector_values(sec_names: list[str], query_date: str) -> dict[str, float]:
    """
    批量查询板块指数（按日期）

    Args:
        sec_names: 板块名称列表
        query_date: 查询日期 (YYYY-MM-DD)

    Returns:
        {板块名: 指数值}
    """
    if not sec_names:
        return {}

    values = {}

    if len(sec_names) == 1:
        # 单板块: "板块名,日期 收盘价、开盘价、涨跌幅"
        question = f"{sec_names[0]},{query_date} 收盘价、开盘价、涨跌幅"
    else:
        # 多板块: "板块1,板块2,板块3,日期 收盘价、开盘价、涨跌幅" (逗号分隔)
        question = f"{','.join(sec_names)},{query_date} 收盘价、开盘价、涨跌幅"

    result = query_wencai(question, secondary_intent="zhishu", page=1, perpage=len(sec_names))

    if result["status"] != "success":
        return {}

    for item in result.get("data", []):
        sector_name = item.get("name", "")
        price = item.get("price")
        if sector_name and price is not None:
            values[sector_name] = price

    return values


def get_latest_batch_news(top_n: int) -> list[dict]:
    """
    获取最新批次中得分最高的前 N 条新闻

    Returns:
        [{id, title, related_sectors, publish_time, created_at, importance_score}, ...]
    """
    latest_batch_id = db_importance.get_max_batch_id()
    if not latest_batch_id:
        return []

    return db_importance.get_top_news_by_batch(latest_batch_id, top_n)


def build_sector_values_str(related_sectors: str, index_by_name: dict[str, float]) -> str:
    """
    根据 related_sectors 构建板块指数值字符串

    Args:
        related_sectors: 板块名用 | 分隔 (如 "稀土|芯片")
        index_by_name: {板块名: 指数值}

    Returns:
        格式: 板块名:指数值|板块名:指数值
    """
    if not related_sectors:
        return ""

    parts = []
    for name in related_sectors.split("|"):
        name = name.strip()
        if not name:
            continue

        # 归一化板块名
        matched = normalize(name)
        std_name = None
        for m in matched:
            if m.get("normalized") and m.get("name"):
                std_name = m["name"]
                break

        # 精确匹配归一化后的板块名
        if std_name and std_name in index_by_name:
            parts.append(f"{std_name}:{index_by_name[std_name]}")
        # fallback: 模糊匹配（包含关系）
        elif std_name:
            for idx_name, idx_value in index_by_name.items():
                if std_name in idx_name or idx_name in std_name:
                    parts.append(f"{idx_name}:{idx_value}")
                    break

    return "|".join(parts)


def run():
    """主流程"""
    # 加载配置
    config = load_config()
    top_n = config.get("top_n", 10)

    print("=" * 50)
    print(f"获取最新批次前 {top_n} 条新闻的发布时板块指数")
    print("=" * 50)

    # 1. 获取最新批次的前 N 条新闻
    print("\n[1/3] 获取最新批次新闻...")
    news_list = get_latest_batch_news(top_n)
    if not news_list:
        print("  未找到新闻数据")
        return

    print(f"  获取到 {len(news_list)} 条新闻")

    # 2. 按交易时段和日期分组
    print("\n[2/3] 分组合并查询...")

    # {(period, date): [new_id, ...], (period, date): [sec_names, ...]}
    groups = defaultdict(lambda: {"news_ids": [], "sec_names": set()})

    for news in news_list:
        pub_time = news.get("publish_time", "")
        if not pub_time:
            pub_time = news.get("created_at", "")

        period = parse_period(pub_time)
        query_date = get_query_date(pub_time, period)
        key = (period, query_date)

        groups[key]["news_ids"].append(news["id"])

        # 解析关联板块
        related = news.get("related_sectors", "")
        if related:
            for sec in related.split("|"):
                sec = sec.strip()
                if sec:
                    groups[key]["sec_names"].add(sec)

    # 显示分组信息
    for (period, date), group in groups.items():
        period_name = "盘前" if period == "pre_market" else "盘中/盘后"
        print(f"  {period_name} {date}: {len(group['news_ids'])} 条新闻, {len(group['sec_names'])} 个板块")

    # 3. 批量查询并更新
    print("\n[3/3] 查询并更新板块指数...")

    total_updated = 0

    for (period, query_date), group in groups.items():
        sec_names = list(group["sec_names"])
        if not sec_names:
            continue

        # 查询板块指数
        index_values = fetch_sector_values(sec_names, query_date)
        if not index_values:
            print(f"  查询失败: {period} {query_date}")
            continue

        print(f"  查询到 {len(index_values)} 个板块指数")

        # 构建批量更新列表
        updates = []
        for news in news_list:
            if news["id"] not in group["news_ids"]:
                continue

            related = news.get("related_sectors", "")
            value_str = build_sector_values_str(related, index_values)

            if value_str:
                updates.append((news["id"], value_str))

        # 批量更新
        if updates:
            db_importance.batch_update_publish_sector_values(updates)
            total_updated += len(updates)

    print(f"\n更新完成，共更新 {total_updated} 条")


if __name__ == "__main__":
    run()