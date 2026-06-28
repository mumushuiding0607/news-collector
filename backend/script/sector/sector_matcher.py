"""
sector_matcher.py - 板块匹配策略

支持：精确匹配、拼音首字母匹配、关键词匹配、模糊匹配

重要：
  所有 DB 操作通过 get_conn()，禁止直接实例化 sqlite3.Connection。
"""

from script.sector.pinyin import to_pinyin_initial
from script.db import get_conn
from script.db.connection import put_conn


def search(keyword: str, limit: int = 5) -> list[dict]:
    """搜索板块（支持拼音首字母、名称关键词、简称）"""
    if not keyword:
        return []
    keyword = keyword.strip()
    results = []
    conn = get_conn()

    row = conn.execute(
        "SELECT code, name FROM sectors WHERE name = ? LIMIT 1",
        (keyword,)
    ).fetchone()
    if row:
        results.append({"code": row[0], "name": row[1], "match_type": "exact"})
    else:
        pinyin_initial = to_pinyin_initial(keyword)
        if pinyin_initial and len(pinyin_initial) >= 2:
            rows = conn.execute("""
                SELECT code, name FROM sectors
                WHERE name_pinyin_initial = ?
                LIMIT ?
            """, (pinyin_initial, limit)).fetchall()
            for row in rows:
                results.append({"code": row[0], "name": row[1], "match_type": "pinyin_initial"})

        if len(results) < limit:
            like_rows = conn.execute("""
                SELECT code, name FROM sectors
                WHERE name LIKE ?
                LIMIT ?
            """, (f"%{keyword}%", limit - len(results))).fetchall()
            for row in like_rows:
                results.append({"code": row[0], "name": row[1], "match_type": "like"})

        if len(results) < limit:
            rows = conn.execute("""
                SELECT code, name FROM sectors
                WHERE keywords LIKE ?
                LIMIT ?
            """, (f"%{keyword}%", limit - len(results))).fetchall()
            for row in rows:
                results.append({"code": row[0], "name": row[1], "match_type": "keyword"})

    put_conn(conn)
    return results[:limit]


def fuzzy_match(raw_name: str) -> dict | None:
    """将LLM输出的原始板块名归一化为标准板块"""
    if not raw_name:
        return None
    raw = raw_name.strip()

    results = search(raw, limit=1)
    if results and results[0]["match_type"] == "exact":
        return results[0]

    pinyin_initial = to_pinyin_initial(raw)
    if pinyin_initial and len(pinyin_initial) >= 2:
        results = search(pinyin_initial, limit=3)
        if results:
            return results[0]

    results = search(raw, limit=5)
    for r in results:
        if r["match_type"] == "keyword":
            return r

    results = search(raw, limit=3)
    if results:
        best = results[0]
        if best["match_type"] in ("pinyin_initial", "like", "keyword", "exact"):
            return best

    for suffix in ['行业', '板块', '概念', '设备', '生产', '制造', '相关', '主题']:
        if raw.endswith(suffix):
            core = raw[:-len(suffix)]
            if core and len(core) >= 2:
                results = search(core, limit=3)
                if results:
                    return results[0]

    for core_len in [2, 3, 4]:
        if len(raw) >= core_len:
            core = raw[:core_len]
            if core != raw:
                results = search(core, limit=3)
                if results:
                    best = results[0]
                    if best["match_type"] in ("pinyin_initial", "like", "keyword", "exact"):
                        return best

    for suffix_len in [2, 3, 4]:
        if len(raw) >= suffix_len:
            suffix = raw[-suffix_len:]
            if suffix != raw:
                results = search(suffix, limit=3)
                if results:
                    best = results[0]
                    if best["match_type"] in ("like", "exact"):
                        return best

    return None


def normalize(raw_sectors: str) -> list[dict]:
    """将LLM输出的多板块字串归一化为标准板块列表"""
    results = []
    if not raw_sectors:
        return results
    names = [n.strip() for n in raw_sectors.split("|") if n.strip()]
    for name in names:
        matched = fuzzy_match(name)
        if matched:
            matched["raw"] = name
            matched["normalized"] = True
            results.append(matched)
        else:
            results.append({
                "code": None,
                "name": name,
                "raw": name,
                "normalized": False,
                "match_type": "none"
            })
    return results