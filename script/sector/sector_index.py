"""
sector_index.py - 板块指数查询模块

功能：
  - 批量查询板块当前指数和涨跌幅
  - 查询指定新闻发布瞬间的板块指数（用于评分前10）
  - 零token归一化LLM输出的板块名

使用：
  from sector_index import batch_query_sectors, query_sectors_at_time
"""

import json
import re
from datetime import datetime, timedelta
from typing import Optional

from common.iwencai import query_wencai
from common.db.sectors import normalize


# ==================== 板块指数查询 ====================

def query_sector_index(sector_name: str) -> dict | None:
    """
    查询单个板块的当前指数和涨跌幅

    Args:
        sector_name: 板块名称（如"稀土"、"芯片概念"）

    Returns:
        {"code": "885343", "name": "稀土永磁", "change_rate": "+2.35%", "turnover": "3.5", ...}
    """
    # 先归一化板块名
    matched = normalize(sector_name)
    if not matched or not matched.get("code"):
        return None

    code = matched["code"]
    name = matched["name"]

    # 查询该板块详情
    result = query_wencai(f"{name}板块行情", secondary_intent="zhishu", page=1, perpage=1)
    if result["status"] != "success" or not result["data"]:
        return None

    item = result["data"][0]
    return {
        "code": code,
        "name": name,
        "change_rate": item.get("change_rate", ""),
        "turnover": item.get("turnover", ""),
        "volume": item.get("volume", ""),
        "amount": item.get("amount", ""),
        "dde_net_amount": item.get("dde_net_amount", ""),
    }


def batch_query_sectors(sector_names: list[str], force_update: bool = False) -> list[dict]:
    """
    批量查询多个板块的当前指数

    Args:
        sector_names: 板块名称列表（如["稀土", "芯片", "军工"]）
        force_update: 是否强制刷新（默认False，使用缓存）

    Returns:
        [
            {"code": "885343", "name": "稀土永磁", "change_rate": "+2.35%", "normalized": True},
            {"code": None, "name": "不存在板块", "normalized": False},
        ]
    """
    if not sector_names:
        return []

    # 归一化所有板块名
    normalized = normalize("|".join(sector_names))
    return normalized


def query_sectors_at_time(sector_names: list[str], news_time: str, top_n: int = 10) -> list[dict]:
    """
    查询新闻发布瞬间的板块指数

    用于评分前10的新闻，计算"新闻发布至今"的涨跌幅。

    Args:
        sector_names: 板块名称列表
        news_time: 新闻发布时间（格式：YYYY-MM-DD HH:MM:SS）
        top_n: 只返回评分前N的板块（默认10）

    Note:
        同花顺API不提供历史快照，此函数返回当前指数作为替代参考。
        实际"发布瞬间"指数需要通过日期归档数据获取。
    """
    results = []
    for name in sector_names[:top_n]:
        matched = normalize(name)
        if matched and matched.get("code"):
            result = query_sector_index(matched["name"])
            if result:
                result["news_time"] = news_time
                result["current_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                results.append(result)
    return results


# ==================== 关联板块指数存储 ====================

def save_sector_indices(importance_id: int, sector_data: list[dict], commit: bool = True):
    """
    将板块指数数据存入数据库

    Args:
        importance_id: importance表记录ID
        sector_data: 板块指数列表
        commit: 是否立即提交
    """
    from common.db.connection import get_conn

    conn = get_conn()
    try:
        for sector in sector_data:
            conn.execute("""
                INSERT OR REPLACE INTO sector_indices
                    (importance_id, sector_code, sector_name, change_rate, volume, amount, dde_net_amount, query_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now','localtime'))
            """, (
                importance_id,
                sector.get("code", ""),
                sector.get("name", ""),
                sector.get("change_rate", ""),
                sector.get("volume", ""),
                sector.get("amount", ""),
                sector.get("dde_net_amount", ""),
            ))
        if commit:
            conn.commit()
    finally:
        conn.close()


def get_sector_indices(importance_id: int) -> list[dict]:
    """读取某条新闻的关联板块指数"""
    from common.db.connection import get_conn

    conn = get_conn()
    cur = conn.execute("""
        SELECT sector_code, sector_name, change_rate, volume, amount, dde_net_amount, query_time
        FROM sector_indices
        WHERE importance_id = ?
        ORDER BY query_time DESC
    """, (importance_id,))
    rows = cur.fetchall()
    conn.close()

    return [
        {
            "sector_code": row[0],
            "sector_name": row[1],
            "change_rate": row[2],
            "volume": row[3],
            "amount": row[4],
            "dde_net_amount": row[5],
            "query_time": row[6],
        }
        for row in rows
    ]


def ensure_sector_indices_table():
    """确保sector_indices表存在"""
    from common.db.connection import get_conn

    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sector_indices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            importance_id INTEGER NOT NULL,
            sector_code TEXT,
            sector_name TEXT,
            change_rate TEXT,
            volume TEXT,
            amount TEXT,
            dde_net_amount TEXT,
            query_time TEXT DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (importance_id) REFERENCES importance(id)
        )
    """)
    conn.commit()
    conn.close()


# ==================== CLI入口 ====================

def main():
    """命令行入口"""
    import sys

    args = sys.argv[1:]

    if not args:
        print("用法: python -m sector_index <命令> [参数]")
        print("")
        print("命令:")
        print("  query <板块名>              - 查询单个板块指数")
        print("  batch <板块1,板块2,...>    - 批量归一化板块名")
        print("  normalize <板块串>         - 归一化多板块（|分隔）")
        sys.exit(1)

    cmd = args[0]

    if cmd == "query":
        if len(args) < 2:
            print("错误: 需要板块名")
            sys.exit(1)
        result = query_sector_index(args[1])
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif cmd == "batch":
        if len(args) < 2:
            print("错误: 需要板块名列表（逗号分隔）")
            sys.exit(1)
        names = [n.strip() for n in args[1].split(",")]
        results = batch_query_sectors(names)
        for r in results:
            status = "OK" if r["normalized"] else "FAIL"
            print(f"  [{status}] {r['name']} ({r.get('code', 'N/A')})")

    elif cmd == "normalize":
        if len(args) < 2:
            print("错误: 需要板块名串（|分隔）")
            sys.exit(1)
        raw = args[1]
        results = normalize(raw)
        for r in results:
            status = "OK" if r["normalized"] else "FAIL"
            print(f"  [{status}] {r['raw']} -> {r['name']} ({r.get('code', 'N/A')})")

    else:
        print(f"未知命令: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()