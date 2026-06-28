"""
db/backtest_db.py - 回测数据库访问层

封装 backtest_results 表的操作和回测工作流。
"""
from __future__ import annotations
import json
from datetime import datetime, timedelta
from script.db import get_conn, put_conn


def ensure_table() -> None:
    """建表（幂等）"""
    conn = get_conn()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS backtest_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                news_id INTEGER NOT NULL,
                valid_comments TEXT,
                optimization_suggestions TEXT,
                raw_llm_result TEXT,
                created_at TEXT DEFAULT (datetime('now','localtime'))
            )
        """)
        conn.commit()
    finally:
        put_conn(conn)


def _backtest_news_impl(news_id: int, conn) -> dict | None:
    """回测某条新闻（内部用 conn）"""
    row = conn.execute(
        "SELECT id, title, summary, reason, related_sectors, importance_score "
        "FROM importance WHERE id = ?", (news_id,)
    ).fetchone()
    if not row:
        return None

    news = {
        "id": row[0],
        "title": row[1] or "",
        "summary": row[2] or "",
        "reason": row[3] or "",
        "related_sectors": row[4] or "",
        "importance_score": row[5] or 0,
    }

    comment_rows = conn.execute(
        "SELECT id, content FROM comments WHERE news_id = ? ORDER BY created_at DESC",
        (news_id,),
    ).fetchall()
    comments = [{"id": r[0], "content": r[1] or ""} for r in comment_rows]
    return {"news": news, "comments": comments}


def run_backtest(news_id: int | None = None, days: int | None = None) -> list:
    """
    执行回测工作流。

    Args:
        news_id: 指定新闻ID（单独回测）
        days: 回测最近N天

    Returns:
        回测结果列表
    """
    from script.backtest.evaluator import call_llm, build_prompt

    conn = get_conn()
    try:
        ensure_table()

        if news_id is not None:
            data = _backtest_news_impl(news_id, conn)
            if not data:
                return []
            result = _process_backtest(data, conn)
            return [result] if result else []

        if days is not None:
            since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
            rows = conn.execute(
                "SELECT id FROM importance WHERE created_at >= ? ORDER BY created_at DESC",
                (since,)
            ).fetchall()
            results = []
            for (nid,) in rows:
                data = _backtest_news_impl(nid, conn)
                if data:
                    result = _process_backtest(data, conn)
                    if result:
                        results.append(result)
            return results

        return []
    finally:
        put_conn(conn)


def _process_backtest(data: dict, conn) -> dict | None:
    """处理单条回测（内部用 conn）"""
    from script.backtest.evaluator import call_llm, build_prompt

    news, comments = data["news"], data["comments"]
    news_id = news["id"]

    prompt = build_prompt(news, comments)
    result = call_llm(prompt)

    if result is None:
        return None

    valid_comments = json.dumps(result.get("有效评论") or [], ensure_ascii=False)
    suggestions = json.dumps(result.get("优化建议") or [], ensure_ascii=False)

    conn.execute("""
        INSERT INTO backtest_results
            (news_id, valid_comments, optimization_suggestions, raw_llm_result)
        VALUES (?, ?, ?, ?)
    """, (news_id, valid_comments, suggestions, json.dumps(result, ensure_ascii=False)))
    conn.commit()
    return result
