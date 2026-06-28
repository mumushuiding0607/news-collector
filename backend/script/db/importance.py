"""
db/importance.py - 新闻评分表 CRUD

重要：
  表结构定义在 db/schema.sql 中，不要在此文件中硬编码建表语句。

表结构 (importance):
  id, news_id, batch_id, source_name, title, url, publish_time,
  summary, related_sectors, importance_score, reason,
  direction, intensity, expected_change, duration,
  expectation_level, market_mode, publish_sector_values,
  current_sector_values, created_at

初始化：
  表由 schema.sql 统一创建，如需单独初始化可调用 init_db()。
"""

from .connection import get_conn, put_conn


# ---------------------------------------------------------------------------
# 写
# ---------------------------------------------------------------------------

def insert(row: dict, commit: bool = True) -> int | None:
    """
    写入一条评分记录到 importance 表。

    row 字段：
        news_id, batch_id, source_name, title, url, publish_time,
        summary, related_sectors, importance_score, reason,
        direction, intensity, expected_change, duration,
        expectation_level, market_mode, publish_sector_values,
        current_sector_values

    返回:
        新记录 id（int），失败返回 None
    """
    conn = get_conn()
    try:
        # INSERT OR IGNORE：news_id 唯一索引，同一新闻重复评分时静默跳过，
        # 避免并发跑分或 status 状态机异常导致 importance 表出现重复行。
        cur = conn.execute("""
            INSERT OR IGNORE INTO importance
                (news_id, batch_id, source_name, title, url, publish_time,
                 summary, related_sectors, importance_score, reason,
                 direction, intensity, expected_change, duration,
                 expectation_level, market_mode, publish_sector_values,
                 current_sector_values, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now','localtime'))
        """, (
            row["news_id"],
            row.get("batch_id", 0),
            row["source_name"],
            row["title"],
            row["url"],
            row["publish_time"],
            row["summary"],
            row["related_sectors"],
            row["importance_score"],
            row["reason"],
            row.get("direction", ""),
            row.get("intensity", 0),
            row.get("expected_change", ""),
            row.get("duration", ""),
            row.get("expectation_level", ""),
            row.get("market_mode", ""),
            row.get("publish_sector_values", ""),
            row.get("current_sector_values", ""),
        ))
        if commit:
            conn.commit()
        return cur.lastrowid
    except Exception:
        return None
    finally:
        put_conn(conn)


# ---------------------------------------------------------------------------
# 读
# ---------------------------------------------------------------------------

def get_recent(limit: int = 20) -> list[tuple]:
    """读取最近评分的新闻（按创建时间倒序）"""
    conn = get_conn()
    cur = conn.execute("""
        SELECT id, news_id, source_name, title, url, publish_time,
               summary, related_sectors, importance_score, reason,
               direction, intensity, expected_change, duration,
               expectation_level, market_mode, publish_sector_values,
               current_sector_values, created_at
        FROM importance
        ORDER BY created_at DESC
        LIMIT ?
    """, (limit,))
    rows = cur.fetchall()
    put_conn(conn)
    return rows


def get_by_score(min_score: int = 7, limit: int = 20) -> list[tuple]:
    """读取评分 >= min_score 的新闻（高重要性）"""
    conn = get_conn()
    cur = conn.execute("""
        SELECT id, news_id, source_name, title, url, publish_time,
               summary, related_sectors, importance_score, reason,
               direction, intensity, expected_change, duration,
               expectation_level, market_mode, publish_sector_values,
               current_sector_values, created_at
        FROM importance
        WHERE importance_score >= ?
        ORDER BY importance_score DESC, created_at DESC
        LIMIT ?
    """, (min_score, limit))
    rows = cur.fetchall()
    put_conn(conn)
    return rows


def get_latest_batch(limit: int = 20) -> list[tuple]:
    """读取最新一批次的新闻（按created_at分组）"""
    conn = get_conn()
    # 获取最新的批次时间
    latest_time = conn.execute("""
        SELECT created_at FROM importance ORDER BY created_at DESC LIMIT 1
    """).fetchone()
    if not latest_time:
        put_conn(conn)
        return []

    cur = conn.execute("""
        SELECT id, news_id, source_name, title, url, publish_time,
               summary, related_sectors, importance_score, reason,
               direction, intensity, expected_change, duration,
               expectation_level, market_mode, publish_sector_values,
               current_sector_values, created_at
        FROM importance
        WHERE created_at = ?
        ORDER BY importance_score DESC
        LIMIT ?
    """, (latest_time[0], limit))
    rows = cur.fetchall()
    put_conn(conn)
    return rows


def get_max_batch_id() -> int | None:
    """获取最新的 batch_id"""
    conn = get_conn()
    try:
        row = conn.execute("SELECT MAX(batch_id) FROM importance").fetchone()
        return row[0] if row and row[0] is not None else None
    finally:
        put_conn(conn)


def get_latest_importance_date() -> str | None:
    """获取 importance 表中最新新闻的日期（按 batch_id 最大批次推断）"""
    conn = get_conn()
    try:
        row = conn.execute("""
            SELECT date(publish_time, 'localtime') FROM importance
            WHERE batch_id = (SELECT MAX(batch_id) FROM importance)
              AND date(publish_time, 'localtime') IS NOT NULL
            LIMIT 1
        """).fetchone()
        return row[0] if row and row[0] else None
    finally:
        put_conn(conn)


def get_positive_by_date(date_str: str, min_score: int = 6, limit: int = 200) -> list:
    """获取指定日期的积极新闻（按重要性评分倒序）"""
    conn = get_conn()
    try:
        cur = conn.execute("""
            SELECT id, news_id, source_name, title, url, publish_time,
                   summary, related_sectors, importance_score, reason,
                   direction, intensity, expected_change, duration,
                   expectation_level, market_mode, created_at
            FROM importance
            WHERE date(publish_time, 'localtime') = date(?)
              AND direction = '积极'
              AND importance_score >= ?
            ORDER BY importance_score DESC
            LIMIT ?
        """, (date_str, min_score, limit))
        return cur.fetchall()
    finally:
        put_conn(conn)


def get_top_news_by_batch(batch_id: int, top_n: int = 10) -> list[dict]:
    """获取指定批次中得分最高的前 N 条新闻"""
    conn = get_conn()
    try:
        cur = conn.execute("""
            SELECT id, title, related_sectors, publish_time, created_at, importance_score
            FROM importance
            WHERE batch_id = ?
            ORDER BY importance_score DESC
            LIMIT ?
        """, (batch_id, top_n))
        return [
            {
                "id": r[0],
                "title": r[1],
                "related_sectors": r[2],
                "publish_time": r[3],
                "created_at": r[4],
                "importance_score": r[5],
            }
            for r in cur.fetchall()
        ]
    finally:
        put_conn(conn)


def update_publish_sector_values(news_id: int, value_str: str) -> bool:
    """更新单条新闻的 publish_sector_values"""
    conn = get_conn()
    try:
        conn.execute("""
            UPDATE importance
            SET publish_sector_values = ?
            WHERE id = ?
        """, (value_str, news_id))
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        put_conn(conn)


def batch_update_publish_sector_values(updates: list[tuple[int, str]]) -> int:
    """
    批量更新 publish_sector_values

    Args:
        updates: list of (news_id, value_str)

    Returns:
        更新的记录数
    """
    if not updates:
        return 0
    conn = get_conn()
    try:
        for news_id, value_str in updates:
            conn.execute("""
                UPDATE importance
                SET publish_sector_values = ?
                WHERE id = ?
            """, (value_str, news_id))
        conn.commit()
        return len(updates)
    finally:
        put_conn(conn)


def sync_sector_values_batch(
    index_by_code: dict[str, float],
    index_by_name: dict[str, float],
    change_rate_by_name: dict[str, float],
    recent_days: int = 7,
) -> tuple[int, int, int]:
    """
    批量同步板块指数值到 importance 表。

    - publish_sector_values: 首次填充（空则填）
    - current_sector_values: 高分 + 最近N天 + 有关联板块
    - current_sector_change_rates: 当前涨跌幅
    - max_sector_rise: 7天内板块最大涨幅（大于前值则更新）

    Returns:
        (publish填充数, current更新数, max_rise更新数)
    """
    from datetime import datetime, timedelta

    seven_days_ago = (datetime.now() - timedelta(days=recent_days)).strftime("%Y-%m-%d %H:%M:%S")

    def build_value_string(sector_names: str) -> str:
        """根据 related_sectors 字段构建指数值字符串"""
        if not sector_names:
            return ""
        unique_names = list(dict.fromkeys(n.strip() for n in sector_names.split("|") if n.strip()))
        parts = []
        for name in unique_names:
            from script.db.sectors import normalize
            matched_list = normalize(name)
            for matched in matched_list:
                if matched.get("normalized") and matched.get("code"):
                    code = matched["code"]
                    std_name = matched["name"]
                    if code in index_by_code:
                        parts.append(f"{std_name}:{index_by_code[code]}")
                        break
                    elif std_name in index_by_name:
                        parts.append(f"{std_name}:{index_by_name[std_name]}")
                        break
        return "|".join(parts)

    def build_change_rate_string(sector_names: str) -> str:
        """根据 related_sectors 字段构建板块涨跌幅字符串"""
        if not sector_names:
            return ""
        unique_names = list(dict.fromkeys(n.strip() for n in sector_names.split("|") if n.strip()))
        parts = []
        for name in unique_names:
            from script.db.sectors import normalize
            matched_list = normalize(name)
            for matched in matched_list:
                if matched.get("normalized") and matched.get("name"):
                    std_name = matched["name"]
                    if std_name in change_rate_by_name:
                        parts.append(f"{change_rate_by_name[std_name]}")
                        break
        return "|".join(parts)

    def calculate_max_rise(publish_str: str, current_str: str) -> float:
        """计算板块最大涨幅"""
        if not publish_str or not current_str:
            return 0.0
        def parse(s):
            r = {}
            if not s:
                return r
            for part in s.split("|"):
                part = part.strip()
                if not part or ":" not in part:
                    continue
                name, val = part.rsplit(":", 1)
                try:
                    r[name.strip()] = float(val)
                except ValueError:
                    pass
            return r
        publish_map = parse(publish_str)
        current_map = parse(current_str)
        max_rise = 0.0
        for name, publish_val in publish_map.items():
            if publish_val and publish_val > 0 and name in current_map:
                current_val = current_map[name]
                if current_val:
                    rise = (current_val - publish_val) / publish_val * 100
                    if rise > max_rise:
                        max_rise = rise
        return round(max_rise, 2)

    conn = get_conn()
    try:
        # 确保 current_sector_change_rates 列存在
        try:
            conn.execute("ALTER TABLE importance ADD COLUMN current_sector_change_rates TEXT")
        except Exception:
            pass

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
            value_str = build_value_string(related_sectors)
            change_rate_str = build_change_rate_string(related_sectors)
            if not value_str:
                continue

            should_update_publish = not publish_values
            should_update_current = importance_score >= 7 and created_at >= seven_days_ago
            new_max_rise = 0.0
            if should_update_current and current_values and publish_values:
                new_max_rise = calculate_max_rise(publish_values, value_str)
            elif should_update_current and publish_values:
                new_max_rise = calculate_max_rise(publish_values, value_str)
            should_update_max_rise = new_max_rise > (prev_max_rise or 0)

            if should_update_publish and should_update_current:
                conn.execute("""
                    UPDATE importance
                    SET publish_sector_values = ?, current_sector_values = ?,
                        current_sector_change_rates = ?, max_sector_rise = ?
                    WHERE id = ?
                """, (value_str, value_str, change_rate_str, new_max_rise, importance_id))
                publish_count += 1
                current_count += 1
                if should_update_max_rise:
                    max_rise_count += 1
            elif should_update_publish:
                conn.execute("""
                    UPDATE importance
                    SET publish_sector_values = ?, current_sector_change_rates = ?, max_sector_rise = ?
                    WHERE id = ?
                """, (value_str, change_rate_str, new_max_rise, importance_id))
                publish_count += 1
            elif should_update_current:
                conn.execute("""
                    UPDATE importance
                    SET current_sector_values = ?, current_sector_change_rates = ?, max_sector_rise = ?
                    WHERE id = ?
                """, (value_str, change_rate_str, new_max_rise, importance_id))
                current_count += 1
                if should_update_max_rise:
                    max_rise_count += 1

        conn.commit()
        return publish_count, current_count, max_rise_count
    finally:
        put_conn(conn)


def get_high_score_no_sector_news(min_score: int = 8) -> list[dict]:
    """获取高分但无板块的新闻"""
    conn = get_conn()
    try:
        rows = conn.execute("""
            SELECT id, title, summary, reason
            FROM importance
            WHERE importance_score >= ?
              AND (related_sectors IS NULL OR related_sectors = '')
            ORDER BY importance_score DESC
        """, (min_score,)).fetchall()
        return [
            {"id": r[0], "title": r[1] or "", "summary": r[2] or "", "reason": r[3] or ""}
            for r in rows
        ]
    finally:
        put_conn(conn)


def update_related_sectors(news_id: int, sectors: list[str]) -> bool:
    """更新新闻的关联板块"""
    if not sectors:
        return False
    conn = get_conn()
    try:
        conn.execute("""
            UPDATE importance
            SET related_sectors = ?
            WHERE id = ?
        """, ("|".join(sectors), news_id))
        conn.commit()
        return True
    finally:
        put_conn(conn)