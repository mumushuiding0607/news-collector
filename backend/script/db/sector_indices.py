"""
db/sector_indices.py - 板块指数记录表 CRUD

重要：
  所有 sector_indices 表的操作必须通过此模块。
"""

from .connection import get_conn, put_conn


def save_sector_indices(importance_id: int, sector_data: list[dict], commit: bool = True) -> None:
    """
    保存板块指数记录

    Args:
        importance_id: importance表记录ID
        sector_data: 板块指数列表，每个dict包含：
            code, name, change_rate, volume, amount, dde_net_amount
        commit: 是否立即提交
    """
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
        put_conn(conn)


def get_sector_indices(importance_id: int) -> list[dict]:
    """读取某条新闻的关联板块指数"""
    conn = get_conn()
    try:
        cur = conn.execute("""
            SELECT sector_code, sector_name, change_rate, volume, amount, dde_net_amount, query_time
            FROM sector_indices
            WHERE importance_id = ?
            ORDER BY query_time DESC
        """, (importance_id,))
        rows = cur.fetchall()
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
    finally:
        put_conn(conn)