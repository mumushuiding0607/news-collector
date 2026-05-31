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
_BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BASE_DIR))

from api_clients.iwencai import query_wencai
from common.db.sectors import normalize

# 默认只同步最近7天的记录
DEFAULT_RECENT_DAYS = 7


def query_all_sector_indices() -> tuple[dict[str, float], dict[str, float], int]:
    """
    查询所有板块当前指数值，构建 {板块code: 指数值} 和 {板块名: 指数值} 字典

    Returns:
        (index_by_code, index_by_name, total_count)
    """
    # 使用 loop=5 获取所有板块数据（约300+条）
    result = query_wencai("二级行业或二级概念板块", secondary_intent="zhishu", loop=5)
    if result["status"] != "success" or not result["data"]:
        print(f"查询失败: {result.get('message')}")
        return {}, {}, 0

    total_count = result.get("total_count", 0)

    # 同时构建 code->price 和 name->price 两个字典
    index_by_code = {}
    index_by_name = {}
    for item in result["data"]:
        code = item.get("code", "")
        name = item.get("name", "")
        price = item.get("price")
        if code and price:
            index_by_code[code] = price
        if name and price:
            index_by_name[name] = price

    print(f"获取到 {len(index_by_code)}/{total_count} 个板块指数")
    return index_by_code, index_by_name, total_count


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

    parts = []
    for name in sector_names.split("|"):
        name = name.strip()
        if not name:
            continue

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


def sync_values(index_by_code: dict[str, float], index_by_name: dict[str, float]) -> tuple[int, int, int]:
    """
    同步板块指数值到 importance 表
    - publish_sector_values: 首次填充（空则填）
    - current_sector_values: 高分 + 最近7天 + 有关联板块
    - max_sector_rise: 7天内板块最大涨幅（如果大于前值则更新）

    Returns:
        (publish填充数, current更新数, max_rise更新数)
    """
    from common.db.connection import get_conn

    seven_days_ago = (datetime.now() - timedelta(days=DEFAULT_RECENT_DAYS)).strftime("%Y-%m-%d %H:%M:%S")

    conn = get_conn()
    try:
        cur = conn.execute("""
            SELECT id, related_sectors, importance_score, created_at,
                   publish_sector_values, current_sector_values, max_sector_rise
            FROM importance
            WHERE related_sectors IS NOT NULL
              AND related_sectors != ''
        """)
        rows = cur.fetchall()

        publish_count = 0
        current_count = 0
        max_rise_count = 0

        for row in rows:
            importance_id, related_sectors, importance_score, created_at, publish_values, current_values, prev_max_rise = row
            value_str = build_value_string(related_sectors, index_by_code, index_by_name)
            if not value_str:
                continue

            # 判断是否需要填充/更新
            should_update_publish = not publish_values
            should_update_current = (
                importance_score >= 7 and created_at >= seven_days_ago
            )

            # 计算最大涨幅
            new_max_rise = 0.0
            if should_update_current and current_values and publish_values:
                new_max_rise = calculate_max_rise(publish_values, value_str)
            elif should_update_current and publish_values:
                new_max_rise = calculate_max_rise(publish_values, value_str)

            should_update_max_rise = new_max_rise > (prev_max_rise or 0)

            if should_update_publish and should_update_current:
                conn.execute("""
                    UPDATE importance
                    SET publish_sector_values = ?, current_sector_values = ?, max_sector_rise = ?
                    WHERE id = ?
                """, (value_str, value_str, new_max_rise, importance_id))
                publish_count += 1
                current_count += 1
                if should_update_max_rise:
                    max_rise_count += 1
            elif should_update_publish:
                conn.execute("""
                    UPDATE importance
                    SET publish_sector_values = ?, max_sector_rise = ?
                    WHERE id = ?
                """, (value_str, new_max_rise, importance_id))
                publish_count += 1
            elif should_update_current:
                conn.execute("""
                    UPDATE importance
                    SET current_sector_values = ?, max_sector_rise = ?
                    WHERE id = ?
                """, (value_str, new_max_rise, importance_id))
                current_count += 1
                if should_update_max_rise:
                    max_rise_count += 1

        conn.commit()
        print(f"  填充 publish_sector_values: {publish_count} 条")
        print(f"  更新 current_sector_values: {current_count} 条")
        print(f"  更新 max_sector_rise: {max_rise_count} 条")
        return publish_count, current_count, max_rise_count
    finally:
        conn.close()


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
    index_by_code, index_by_name, total_count = result

    # 2. 同步板块指数值
    print("\n[2/2] 同步板块指数值...")
    count1, count2, count3 = sync_values(index_by_code, index_by_name)
    print(f"\n完成！共填充 {count1} 条，更新 {count2} 条，max_rise更新 {count3} 条")


if __name__ == "__main__":
    main()