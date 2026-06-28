"""
news_db.py - 新闻数据库访问层

封装 importance 表的只读查询操作。
"""
from __future__ import annotations
import json
from script.db import get_conn, put_conn


def query_news(where_clause: str = "", params: tuple = (), order_by: str = "importance_score DESC, publish_time DESC", limit: int | None = None) -> list:
    """
    通用新闻查询。

    Returns:
        list of dicts with news fields
    """
    conn = get_conn()
    try:
        base_sql = """
            SELECT id, title, url, source_name, publish_time, summary,
                   related_sectors, importance_score, reason,
                   direction, intensity, expected_change, duration,
                   expectation_level, market_mode, max_sector_rise,
                   publish_sector_values, current_sector_values,
                   current_sector_change_rates, created_at
            FROM importance
        """

        if where_clause:
            sql = f"{base_sql} WHERE {where_clause} ORDER BY {order_by}" + (f" LIMIT ?" if limit else "")
            params_final = (*params, limit) if limit else params
            rows = conn.execute(sql, params_final)
        else:
            sql = f"{base_sql} ORDER BY {order_by}" + (f" LIMIT ?" if limit else "")
            params_final = (limit,) if limit else params
            rows = conn.execute(sql, params_final)

        data = []
        for row in rows.fetchall():
            related = row[6] or ""
            data.append({
                "id": row[0],
                "title": row[1] or "",
                "url": row[2] or "",
                "source_name": row[3] or "",
                "publish_time": row[4],
                "summary": row[5],
                "related_sectors": related,
                "importance_score": row[7],
                "reason": row[8],
                "direction": row[9],
                "intensity": row[10],
                "expected_change": row[11],
                "duration": row[12],
                "expectation_level": row[13],
                "market_mode": row[14],
                "max_sector_rise": row[15],
                "publish_sector_values": row[16],
                "current_sector_values": row[17],
                "current_sector_change_rates": row[18],
                "created_at": row[19],
            })
        return data
    finally:
        put_conn(conn)


def get_news_by_id(news_id: int) -> dict | None:
    """获取单条新闻详情"""
    conn = get_conn()
    try:
        row = conn.execute("""
            SELECT id, title, url, source_name, publish_time, summary,
                   related_sectors, importance_score, reason,
                   direction, intensity, expected_change, duration,
                   expectation_level, market_mode, max_sector_rise,
                   publish_sector_values, current_sector_values,
                   current_sector_change_rates, created_at
            FROM importance WHERE id = ?
        """, (news_id,)).fetchone()
        if not row:
            return None
        return {
            "id": row[0], "title": row[1] or "", "url": row[2] or "",
            "source_name": row[3] or "", "publish_time": row[4],
            "summary": row[5], "related_sectors": row[6],
            "importance_score": row[7], "reason": row[8],
            "direction": row[9], "intensity": row[10],
            "expected_change": row[11], "duration": row[12],
            "expectation_level": row[13], "market_mode": row[14],
            "max_sector_rise": row[15],
            "publish_sector_values": row[16], "current_sector_values": row[17],
            "current_sector_change_rates": row[18], "created_at": row[19],
        }
    finally:
        put_conn(conn)


def query_news_admin(where_clause: str, params: tuple, page: int, limit: int) -> tuple:
    """
    新闻管理分页查询（关联 primary_sources 获取 status）。

    Returns:
        (items: list[dict], total: int)
    """
    conn = get_conn()
    try:
        count_sql = f"""
            SELECT COUNT(*)
            FROM importance i
            JOIN primary_sources p ON p.id = i.news_id
            WHERE {where_clause}
        """
        total = conn.execute(count_sql, params).fetchone()[0]

        offset = (page - 1) * limit
        data_sql = f"""
            SELECT i.id, i.title, i.url, i.source_name, i.publish_time,
                   i.summary, i.related_sectors, i.importance_score, i.reason,
                   i.publish_sector_values, i.current_sector_values,
                   i.current_sector_change_rates, i.created_at,
                   p.status, p.is_useful
            FROM importance i
            JOIN primary_sources p ON p.id = i.news_id
            WHERE {where_clause}
            ORDER BY i.importance_score DESC, i.publish_time DESC
            LIMIT ? OFFSET ?
        """
        rows = conn.execute(data_sql, (*params, limit, offset)).fetchall()

        items = []
        for r in rows:
            items.append({
                "id": r[0], "title": r[1] or "", "url": r[2] or "",
                "source_name": r[3] or "", "publish_time": r[4],
                "summary": r[5], "related_sectors": r[6],
                "importance_score": r[7], "reason": r[8],
                "publish_sector_values": r[9], "current_sector_values": r[10],
                "current_sector_change_rates": r[11], "created_at": r[12],
                "status": r[13], "is_useful": r[14],
            })
        return items, total
    finally:
        put_conn(conn)


def query_primary_sources_admin(where_clause: str, params: tuple, page: int, limit: int) -> tuple:
    """
    新闻管理分页查询（仅 primary_sources，按抓取时间降序）。
    """
    conn = get_conn()
    try:
        count_sql = f"SELECT COUNT(*) FROM primary_sources p WHERE {where_clause}"
        total = conn.execute(count_sql, params).fetchone()[0]

        offset = (page - 1) * limit
        data_sql = f"""
            SELECT p.id, p.source_name, p.title, p.url, p.summary,
                   p.publish_time, p.status, p.is_useful, p.fetched_at, p.content_length
            FROM primary_sources p
            WHERE {where_clause}
            ORDER BY p.fetched_at DESC
            LIMIT ? OFFSET ?
        """
        rows = conn.execute(data_sql, (*params, limit, offset)).fetchall()

        items = []
        for r in rows:
            items.append({
                "id": r[0], "source_name": r[1] or "", "title": r[2] or "",
                "url": r[3] or "", "summary": r[4],
                "publish_time": r[5], "status": r[6],
                "is_useful": r[7], "fetched_at": r[8], "content_length": r[9],
            })
        return items, total
    finally:
        put_conn(conn)


def get_news_source_name(news_id: int) -> str | None:
    """获取新闻的数据源名称（用于权限验证）"""
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT source_name FROM primary_sources WHERE id = ?", (news_id,)
        ).fetchone()
        return row[0] if row else None
    finally:
        put_conn(conn)