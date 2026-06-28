"""
db/news_stocks.py - 新闻-核心标的关联表 CRUD

表结构 (news_stocks):
  id, importance_id, code, name, tier, chain_link, four_dims, moat, news_related,
  d1, d2, d3, created_at
"""

import json
from .connection import get_conn, put_conn


def insert(rows: list[dict], commit: bool = True) -> int:
    """
    批量写入新闻关联的核心标的。

    row 字段：
        importance_id, code, name, tier, chain_link, four_dims, moat, news_related

    返回:
        写入的记录数
    """
    if not rows:
        return 0
    conn = get_conn()
    try:
        count = 0
        for row in rows:
            four_dims_json = json.dumps(row.get("four_dims", {}), ensure_ascii=False) if row.get("four_dims") else ""
            conn.execute("""
                INSERT OR IGNORE INTO news_stocks
                    (importance_id, code, name, tier, chain_link, four_dims, moat, news_related)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                row["importance_id"],
                row.get("code", ""),
                row.get("name", ""),
                row.get("tier", ""),
                row.get("chain_link", ""),
                four_dims_json,
                row.get("moat", ""),
                row.get("news_related", ""),
            ))
            if conn.total_changes > 0:
                count += 1
        if commit:
            conn.commit()
        return count
    finally:
        put_conn(conn)


def get_by_importance(importance_id: int) -> list[dict]:
    """查询某条新闻关联的核心标的"""
    conn = get_conn()
    try:
        cur = conn.execute("""
            SELECT id, importance_id, code, name, tier, chain_link, four_dims, moat, news_related, d1, d2, d3, created_at
            FROM news_stocks
            WHERE importance_id = ?
            ORDER BY tier, code
        """, (importance_id,))
        return [
            {
                "id": r[0],
                "importance_id": r[1],
                "code": r[2],
                "name": r[3],
                "tier": r[4],
                "chain_link": r[5],
                "four_dims": json.loads(r[6]) if r[6] else {},
                "moat": r[7],
                "news_related": r[8],
                "d1": r[9],
                "d2": r[10],
                "d3": r[11],
                "created_at": r[12],
            }
            for r in cur.fetchall()
        ]
    finally:
        put_conn(conn)


def exists(importance_id: int) -> bool:
    """检查某条新闻是否已有关联的核心标的"""
    conn = get_conn()
    try:
        row = conn.execute("""
            SELECT 1 FROM news_stocks WHERE importance_id = ? LIMIT 1
        """, (importance_id,)).fetchone()
        return row is not None
    finally:
        put_conn(conn)


def delete_by_importance(importance_id: int, commit: bool = True) -> int:
    """删除某条新闻关联的核心标的（用于重新生成）"""
    conn = get_conn()
    try:
        conn.execute("DELETE FROM news_stocks WHERE importance_id = ?", (importance_id,))
        if commit:
            conn.commit()
        return conn.total_changes
    finally:
        put_conn(conn)


def get_processed_importance_ids() -> set[int]:
    """获取已生成核心标的的所有 importance_id"""
    conn = get_conn()
    try:
        rows = conn.execute("SELECT DISTINCT importance_id FROM news_stocks").fetchall()
        return {r[0] for r in rows}
    finally:
        put_conn(conn)


def update_d1_d2_d3_batch(updates: list[dict], commit: bool = True) -> dict:
    """
    批量更新新闻关联股票的d1/d2/d3字段。

    一次SQL完成所有更新，按(code, created_at)定位到具体记录。

    Args:
        updates: [{"code": str, "created_at": str, "field": str, "rate": str}, ...]
        commit: 是否提交

    Returns:
        {"d1": count, "d2": count, "d3": count}
    """
    if not updates:
        return {"d1": 0, "d2": 0, "d3": 0}

    conn = get_conn()
    try:
        # 构建 d1/d2/d3 的 CASE WHEN 子句
        d1_cases = []
        d2_cases = []
        d3_cases = []
        all_keys = set()

        for u in updates:
            code = u["code"]
            created = u["created_at"]
            rate = u["rate"]
            when_clause = f"WHEN code = '{code}' AND date(created_at) = '{created}' THEN '{rate}'"
            all_keys.add(code)

            if u["field"] == "d1":
                d1_cases.append(when_clause)
            elif u["field"] == "d2":
                d2_cases.append(when_clause)
            elif u["field"] == "d3":
                d3_cases.append(when_clause)

        # 构建 CASE WHEN 语句
        def build_case(when_clauses):
            if not when_clauses:
                return "d1"  # 不更新则保持原值
            return "CASE " + " ".join(when_clauses) + " ELSE d1 END"

        d1_case = build_case(d1_cases)
        d2_case = build_case(d2_cases).replace("d1", "d2",1).replace("ELSE d2 END", "ELSE d2 END")
        d3_case = build_case(d3_cases).replace("d1", "d3", 1).replace("ELSE d3 END", "ELSE d3 END")

        # 修正 d2_case 和 d3_case
        if d2_cases:
            d2_case = "CASE " + " ".join(d2_cases) + " ELSE d2 END"
        if d3_cases:
            d3_case = "CASE " + " ".join(d3_cases) + " ELSE d3 END"

        codes_list = list(all_keys)
        codes_placeholder = ",".join(["?"] * len(codes_list))

        # 执行批量更新
        conn.execute(f"""
            UPDATE news_stocks
            SET
                d1 = {d1_case},
                d2 = {d2_case},
                d3 = {d3_case}
            WHERE code IN ({codes_placeholder})
        """, codes_list)
        cur = conn.execute("SELECT changes()")
        updated = cur.fetchone()[0]

        if commit:
            conn.commit()

        return {"d1": len(d1_cases), "d2": len(d2_cases), "d3": len(d3_cases), "total": updated}
    finally:
        put_conn(conn)


def get_recent_stocks(days: int = 3) -> dict[str, dict]:
    """
    查询最近N天内的新闻关联股票（去重），返回各股票当前d1/d2/d3值。

    Returns:
        {code: {"d1": str, "d2": str, "d3": str}, ...}
    """
    conn = get_conn()
    try:
        cur = conn.execute("""
            SELECT DISTINCT code, d1, d2, d3
            FROM news_stocks
            WHERE created_at >= datetime('now', ?)
            ORDER BY code
        """, (f'-{days} days',))
        return {
            row[0]: {"d1": row[1], "d2": row[2], "d3": row[3]}
            for row in cur.fetchall()
        }
    finally:
        put_conn(conn)


def get_recent_stocks_with_created(days: int = 3) -> list[dict]:
    """
    查询最近N天内的新闻关联股票，返回各股票及其创建日期。

    Returns:
        [{"code": str, "created_at": str}, ...]
    """
    conn = get_conn()
    try:
        cur = conn.execute("""
            SELECT code, date(created_at) as created_at
            FROM news_stocks
            WHERE created_at >= datetime('now', ?)
            ORDER BY code
        """, (f'-{days} days',))
        return [
            {"code": row[0], "created_at": row[1]}
            for row in cur.fetchall()
        ]
    finally:
        put_conn(conn)


def get_batch_by_importance(news_ids: list[int]) -> dict[int, list[dict]]:
    """
    批量获取多条新闻关联的核心标的。

    Returns:
        {importance_id: [stock_dict, ...], ...}
    """
    if not news_ids:
        return {}
    conn = get_conn()
    try:
        placeholders = ",".join("?" * len(news_ids))
        rows = conn.execute(f"""
            SELECT importance_id, code, name, tier, chain_link, four_dims, moat, news_related, d1, d2, d3
            FROM news_stocks
            WHERE importance_id IN ({placeholders})
            ORDER BY importance_id, tier, code
        """, tuple(news_ids)).fetchall()
        result = {}
        for row in rows:
            iid = row[0]
            if iid not in result:
                result[iid] = []
            result[iid].append({
                "code": row[1],
                "name": row[2],
                "tier": row[3],
                "chain_link": row[4],
                "four_dims": json.loads(row[5]) if row[5] else {},
                "moat": row[6],
                "news_related": row[7],
                "d1": row[8],
                "d2": row[9],
                "d3": row[10],
            })
        return result
    finally:
        put_conn(conn)