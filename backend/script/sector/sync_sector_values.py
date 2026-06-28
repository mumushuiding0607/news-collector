"""
sync_sector_values.py - 同步板块指数值到 importance 表

优化备注（2026-05-30）：
  - 很少使用，无需缓存，每次启动重新查询同花顺全量板块即可

功能：
  - 一次查询同花顺，获取所有板块当前指数值
  - 填充 publish_sector_values（仅首次，即空记录）
  - 更新 current_sector_values（高分 + 最近7天 + 有关联板块）

使用：
  python script/sector/sync_sector_values.py
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# 添加 script 目录到 path
from script.bootstrap import *

from script.api_clients.iwencai import query_wencai
from script.db.sectors import normalize

# 默认只同步最近7天的记录
DEFAULT_RECENT_DAYS = 7


def query_all_sector_indices() -> tuple[dict[str, float], dict[str, float], dict[str, float], int]:
    """
    查询所有板块当前指数值和涨跌幅，构建 {板块code: 指数值}、{板块名: 指数值}、{板块名: 涨跌幅} 字典

    Returns:
        (index_by_code, index_by_name, change_rate_by_name, total_count)
    """
    # 使用新查询获取所有板块（含涨跌幅）
    result = query_wencai(
        "二级概念板块或二级行业板块，涨跌幅排名，成交额，成交量，大单净流入额/流通市值*10000,上涨家数,下跌家数,涨停家数",
        secondary_intent="zhishu", loop=5
    )
    if result["status"] != "success" or not result["data"]:
        print(f"查询失败: {result.get('message')}")
        return {}, {}, {}, 0

    total_count = result.get("total_count", 0)

    index_by_code = {}
    index_by_name = {}
    change_rate_by_name = {}
    for item in result["data"]:
        code = item.get("code", "")
        name = item.get("name", "")
        price = item.get("price")
        change_rate = item.get("change_rate", "")
        if code and price:
            index_by_code[code] = float(price)
        if name and price:
            index_by_name[name] = float(price)
        if name and change_rate:
            try:
                change_rate_by_name[name] = float(change_rate.rstrip("%").lstrip("+"))
            except ValueError:
                pass

    print(f"获取到 {len(index_by_code)}/{total_count} 个板块指数（含涨跌幅）")
    return index_by_code, index_by_name, change_rate_by_name, total_count


def build_value_string(sector_names: str, index_by_code: dict[str, float], index_by_name: dict[str, float]) -> str:
    """
    根据 related_sectors 字段构建指数值字符串

    Args:
        sector_names: 归一化后的板块名，用|分隔（如 "稀土|芯片"）
        index_by_code: {板块code: 指数值} 字典
        index_by_name: {板块名: 指数值} 字典

    Returns:
        格式：板块名:指数值|板块名:指数值
    """
    if not sector_names:
        return ""

    # 去重（保留顺序），避免 related_sectors 中重复板块名导致输出重复
    unique_names = list(dict.fromkeys(n.strip() for n in sector_names.split("|") if n.strip()))

    parts = []
    for name in unique_names:
        # 通过 normalize 获取 code
        matched_list = normalize(name)
        for matched in matched_list:
            if matched.get("normalized") and matched.get("code"):
                code = matched["code"]
                std_name = matched["name"]
                # 优先通过 code 查找
                if code in index_by_code:
                    parts.append(f"{std_name}:{index_by_code[code]}")
                    break
                # fallback 到 name 查找
                elif std_name in index_by_name:
                    parts.append(f"{std_name}:{index_by_name[std_name]}")
                    break

    return "|".join(parts)


def build_change_rate_string(sector_names: str, change_rate_by_name: dict[str, float]) -> str:
    """
    根据 related_sectors 字段构建板块涨跌幅字符串

    Args:
        sector_names: 板块名，用|分隔
        change_rate_by_name: {板块名: 涨跌幅} 字典

    Returns:
        格式：涨跌幅|涨跌幅（按 related_sectors 顺序）
    """
    if not sector_names:
        return ""

    # 去重（保留顺序）
    unique_names = list(dict.fromkeys(n.strip() for n in sector_names.split("|") if n.strip()))

    parts = []
    for name in unique_names:
        matched_list = normalize(name)
        for matched in matched_list:
            if matched.get("normalized") and matched.get("name"):
                std_name = matched["name"]
                if std_name in change_rate_by_name:
                    parts.append(f"{change_rate_by_name[std_name]}")
                    break
                # fallback 模糊匹配
                elif std_name:
                    for idx_name, rate in change_rate_by_name.items():
                        if std_name in idx_name or idx_name in std_name:
                            parts.append(f"{rate}")
                            break

    return "|".join(parts)


def parse_sector_values(value_str: str) -> dict[str, float]:
    """
    解析板块指数值字符串为字典

    Args:
        value_str: 格式 "板块名:指数值|板块名:指数值"

    Returns:
        {板块名: 指数值}
    """
    result = {}
    if not value_str:
        return result
    for part in value_str.split("|"):
        part = part.strip()
        if not part:
            continue
        if ":" in part:
            name, val = part.rsplit(":", 1)
            try:
                result[name.strip()] = float(val)
            except ValueError:
                pass
    return result


def calculate_max_rise(publish_str: str, current_str: str) -> float:
    """
    计算板块最大涨幅

    Args:
        publish_str: 发布时板块指数值字符串
        current_str: 当前板块指数值字符串

    Returns:
        最大涨幅百分比（如 5.23 表示 5.23%）
    """
    if not publish_str or not current_str:
        return 0.0

    publish_map = parse_sector_values(publish_str)
    current_map = parse_sector_values(current_str)

    max_rise = 0.0
    for name, publish_val in publish_map.items():
        if publish_val and publish_val > 0 and name in current_map:
            current_val = current_map[name]
            if current_val:
                rise = (current_val - publish_val) / publish_val * 100
                if rise > max_rise:
                    max_rise = rise

    return round(max_rise, 2)


def sync_values(index_by_code: dict[str, float], index_by_name: dict[str, float], change_rate_by_name: dict[str, float]) -> tuple[int, int, int]:
    """
    同步板块指数值到 importance 表（委托给 importance.sync_sector_values_batch）
    """
    from script.db.importance import sync_sector_values_batch
    return sync_sector_values_batch(index_by_code, index_by_name, change_rate_by_name, recent_days=DEFAULT_RECENT_DAYS)


def main():
    print("=" * 50)
    print("板块指数同步")
    print("=" * 50)

    # 1. 查询同花顺
    print("\n[1/2] 查询同花顺板块指数...")
    result = query_all_sector_indices()
    if not result[0]:
        print("无可用板块指数数据，退出")
        return
    index_by_code, index_by_name, change_rate_by_name, total_count = result

    # 2. 同步板块指数值
    print("\n[2/2] 同步板块指数值...")
    count1, count2, count3 = sync_values(index_by_code, index_by_name, change_rate_by_name)
    print(f"\n完成！共填充 {count1} 条，更新 {count2} 条，max_rise更新 {count3} 条")


if __name__ == "__main__":
    main()