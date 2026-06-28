"""
sectors_crud.py - 板块数据库 CRUD

所有 DB 操作必须通过 get_conn()，禁止直接实例化 sqlite3.Connection。
"""

from script.sector.pinyin import to_pinyin_initial, to_pinyin_full
from script.db import get_conn, put_conn


def count() -> int:
    """返回已存储的板块数量"""
    try:
        conn = get_conn()
        n = conn.execute("SELECT COUNT(*) FROM sectors").fetchone()[0]
        put_conn(conn)
        return n
    except Exception:
        return 0


def list_all() -> list[str]:
    """返回所有板块名称（按 name 排序）"""
    conn = get_conn()
    try:
        rows = conn.execute("SELECT DISTINCT name FROM sectors ORDER BY name").fetchall()
        return [r[0] for r in rows if r[0]]
    finally:
        put_conn(conn)


def insert_or_update(code: str, name: str, keywords: str = "", commit: bool = True) -> int | None:
    """插入或更新板块记录"""
    try:
        conn = get_conn()
        pinyin_initial = to_pinyin_initial(name)
        pinyin_full = to_pinyin_full(name)
        cur = conn.execute("""
            INSERT INTO sectors (code, name, name_pinyin_initial, name_pinyin_full, keywords)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(code) DO UPDATE SET
                name=excluded.name,
                name_pinyin_initial=excluded.name_pinyin_initial,
                name_pinyin_full=excluded.name_pinyin_full,
                keywords=excluded.keywords
        """, (code, name, pinyin_initial, pinyin_full, keywords))
        if commit:
            conn.commit()
        return cur.lastrowid
    except Exception:
        return None
    finally:
        put_conn(conn)


def batch_insert(items: list[dict], commit: bool = True):
    """批量插入板块记录"""
    conn = None
    try:
        conn = get_conn()
        for item in items:
            pinyin_initial = to_pinyin_initial(item["name"])
            pinyin_full = to_pinyin_full(item["name"])
            keywords = item.get("keywords", "")
            conn.execute("""
                INSERT INTO sectors (code, name, name_pinyin_initial, name_pinyin_full, keywords)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(code) DO UPDATE SET
                    name=excluded.name,
                    name_pinyin_initial=excluded.name_pinyin_initial,
                    name_pinyin_full=excluded.name_pinyin_full,
                    keywords=excluded.keywords
            """, (item["code"], item["name"], pinyin_initial, pinyin_full, keywords))
        if commit:
            conn.commit()
    finally:
        if conn:
            put_conn(conn)


def batch_update_keywords(keyword_map: list[tuple[str, str]], commit: bool = True):
    """批量更新板块关键词"""
    try:
        conn = get_conn()
        for name, keywords in keyword_map:
            pinyin_initial = to_pinyin_initial(name)
            conn.execute("""
                UPDATE sectors SET keywords = ?, name_pinyin_initial = ?
                WHERE name = ?
            """, (keywords, pinyin_initial, name))
        if commit:
            conn.commit()
    finally:
        put_conn(conn)


def upsert_sector(code: str, name: str, keywords: str = "", commit: bool = True) -> int | None:
    """插入或更新板块记录（upsert_sector 别名）"""
    return insert_or_update(code, name, keywords, commit)


def sync_from_iwencai(loop: int = 5) -> dict:
    """从同花顺同步全部板块数据"""
    from script.api_clients.iwencai import query_wencai
    result = query_wencai("二级概念板块或二级行业板块", secondary_intent="zhishu", page=1, perpage=100, loop=loop)
    if result["status"] != "success":
        return {"status": "error", "message": f"查询失败: {result.get('message')}"}
    items = []
    for item in result["data"]:
        items.append({
            "code": item.get("code", ""),
            "name": item.get("name", ""),
            "keywords": "",
        })
    before_count = count()
    batch_insert(items)
    after_count = count()
    return {
        "status": "success",
        "added": after_count - before_count,
        "total": after_count,
        "sample": items[:3]
    }