"""
db/sectors.py - 板块数据库管理

重要：
  表结构定义在 db/schema.sql 中，不要在此文件中硬编码建表语句。

功能：
  - 从同花顺获取全部板块数据（二级概念/行业板块，共480条）
  - 预计算拼音首字母、简称等同义词
  - 支持精确匹配、拼音匹配、FTS5全文搜索
  - 零token的板块归一化

初始化：
  表由 schema.sql 统一创建，包括 sectors 表、FTS5虚拟表和触发器。
  如需单独初始化，可调用 init_db()。

依赖：
  - iwencai 模块（用于获取板块数据）
  - pypinyin（用于拼音转换）：pip install pypinyin
"""

import sqlite3
import re
from pathlib import Path

# ==================== 路径配置 ====================

_MODULE_DIR = Path(__file__).parent
_BASE_DIR = _MODULE_DIR.parent.parent.parent
PRIMARY_DB = _BASE_DIR / "db" / "primary.db"


# ==================== 拼音转换 ====================

try:
    from pypinyin import lazy_pinyin

    def to_pinyin_initial(text: str) -> str:
        """获取汉字串的首字母拼音"""
        if not text:
            return ""
        py = lazy_pinyin(text)
        return "".join(w[0] if w else "" for w in py)

    def to_pinyin_full(text: str) -> str:
        """获取汉字串的完整拼音（无声调）"""
        if not text:
            return ""
        return "".join(lazy_pinyin(text))

except ImportError:
    def to_pinyin_initial(text: str) -> str:
        return ""

    def to_pinyin_full(text: str) -> str:
        return ""
    print("[警告] pypinyin 未安装，拼音匹配功能不可用。请运行: pip install pypinyin")


# ==================== 数据库连接 ====================

def _get_conn() -> sqlite3.Connection:
    """获取 primary.db 连接"""
    conn = sqlite3.connect(str(PRIMARY_DB))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


def count() -> int:
    """返回已存储的板块数量"""
    try:
        conn = _get_conn()
        n = conn.execute("SELECT COUNT(*) FROM sectors").fetchone()[0]
        conn.close()
        return n
    except Exception:
        return 0


# ==================== 板块数据写入 ====================

def insert_or_update(code: str, name: str, keywords: str = "", commit: bool = True) -> int | None:
    """插入或更新板块记录"""
    try:
        conn = _get_conn()
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
        conn.close()


def batch_insert(items: list[dict], commit: bool = True):
    """批量插入板块记录"""
    conn = None
    try:
        conn = _get_conn()
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
            conn.close()


# ==================== 板块检索 ====================

def search(keyword: str, limit: int = 5) -> list[dict]:
    """搜索板块（支持拼音首字母、名称关键词、简称）"""
    if not keyword:
        return []
    keyword = keyword.strip()
    results = []
    conn = _get_conn()

    # 1. 精确匹配（名称完全一致）
    row = conn.execute(
        "SELECT code, name FROM sectors WHERE name = ? LIMIT 1",
        (keyword,)
    ).fetchone()
    if row:
        results.append({"code": row[0], "name": row[1], "match_type": "exact"})
    else:
        # 2. 拼音首字母匹配（仅精确匹配，避免短拼音串误匹配）
        pinyin_initial = to_pinyin_initial(keyword)
        if pinyin_initial and len(pinyin_initial) >= 2:
            # 精确匹配拼音首字母（长度>=2时）
            rows = conn.execute("""
                SELECT code, name FROM sectors
                WHERE name_pinyin_initial = ?
                LIMIT ?
            """, (pinyin_initial, limit)).fetchall()
            for row in rows:
                results.append({"code": row[0], "name": row[1], "match_type": "pinyin_initial"})

        # 3. LIKE模糊匹配（替代FTS5，因FTS5中文有问题）
        if len(results) < limit:
            like_rows = conn.execute("""
                SELECT code, name FROM sectors
                WHERE name LIKE ?
                LIMIT ?
            """, (f"%{keyword}%", limit - len(results))).fetchall()
            for row in like_rows:
                results.append({"code": row[0], "name": row[1], "match_type": "like"})

        # 4. keywords模糊匹配
        if len(results) < limit:
            rows = conn.execute("""
                SELECT code, name FROM sectors
                WHERE keywords LIKE ?
                LIMIT ?
            """, (f"%{keyword}%", limit - len(results))).fetchall()
            for row in rows:
                results.append({"code": row[0], "name": row[1], "match_type": "keyword"})

    conn.close()
    return results[:limit]


def fuzzy_match(raw_name: str) -> dict | None:
    """将LLM输出的原始板块名归一化为标准板块"""
    if not raw_name:
        return None
    raw = raw_name.strip()

    # 1. 精确匹配（名称完全一致）
    results = search(raw, limit=1)
    if results and results[0]["match_type"] == "exact":
        return results[0]

    # 2. 拼音首字母匹配（支持拼音输入）
    pinyin_initial = to_pinyin_initial(raw)
    if pinyin_initial and len(pinyin_initial) >= 2:
        results = search(pinyin_initial, limit=3)
        if results:
            return results[0]

    # 3. keywords 匹配（别名映射）
    results = search(raw, limit=5)
    for r in results:
        if r["match_type"] == "keyword":
            return r

    # 4. 模糊匹配（包含匹配）
    results = search(raw, limit=3)
    if results:
        best = results[0]
        if best["match_type"] in ("pinyin_initial", "like", "keyword", "exact"):
            return best

    # 5. 移除常见后缀词后匹配（电力设备 -> 电力）
    for suffix in ['行业', '板块', '概念', '设备', '生产', '制造', '相关', '主题']:
        if raw.endswith(suffix):
            core = raw[:-len(suffix)]
            if core and len(core) >= 2:
                results = search(core, limit=3)
                if results:
                    return results[0]

    # 6. 提取核心词匹配（尝试不同长度的前缀）
    for core_len in [2, 3, 4]:
        if len(raw) >= core_len:
            core = raw[:core_len]
            if core != raw:
                results = search(core, limit=3)
                if results:
                    best = results[0]
                    if best["match_type"] in ("pinyin_initial", "like", "keyword", "exact"):
                        return best

    # 7. 尝试截取后缀（取最后2-4个字符）
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
    """
    将LLM输出的多板块字串归一化为标准板块列表

    Args:
        raw_sectors: "贵金属|黄金|地缘政治" 格式的字串

    Returns:
        [
            {"code": "884215", "name": "稀土", "raw": "稀土", "normalized": True},
            {"code": None, "name": "地缘政治", "raw": "地缘政治", "normalized": False},
        ]
    """
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


# ==================== 初始化板块数据 ====================

def sync_from_iwencai(loop: int = 5) -> dict:
    """
    从同花顺同步全部板块数据（二级概念/行业板块，共480条）

    Args:
        loop: 循环次数（每轮100条，默认5轮=500条）

    Returns:
        {"status": "success", "added": 480, "total": 480}
    """
    from common.iwencai import query_wencai

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


# ==================== 批量更新关键词 ====================

def batch_update_keywords(keyword_map: list[tuple[str, str]], commit: bool = True):
    """
    批量更新板块关键词

    Args:
        keyword_map: [("板块名", "关键词1,关键词2"), ...]
    """
    try:
        conn = _get_conn()
        for name, keywords in keyword_map:
            pinyin_initial = to_pinyin_initial(name)
            conn.execute("""
                UPDATE sectors SET keywords = ?, name_pinyin_initial = ?
                WHERE name = ?
            """, (keywords, pinyin_initial, name))
        if commit:
            conn.commit()
    finally:
        conn.close()


# ==================== CLI入口 ====================

def main():
    """命令行入口"""
    import sys

    args = sys.argv[1:]

    if not args:
        print("用法: python -m db.sectors <命令>")
        print("")
        print("命令:")
        print("  count                    - 查看已存储板块数量")
        print("  sync [loop=5]           - 从同花顺同步板块数据")
        print("  search <关键词>          - 搜索板块")
        print("  normalize <板块名>       - 归一化匹配单个板块")
        print("  normalize-all <板块串>  - 归一化多板块（用|分隔）")
        print("")
        print("示例:")
        print("  python -m db.sectors sync")
        print("  python -m db.sectors search 集成电路")
        print("  python -m db.sectors normalize chip")
        sys.exit(1)

    cmd = args[0]

    if cmd == "count":
        print(f"已存储板块: {count()} 条")

    elif cmd == "sync":
        loop = int(args[1]) if len(args) > 1 else 5
        print(f"正在同步板块数据 (loop={loop})...")
        result = sync_from_iwencai(loop=loop)
        print(f"结果: {result}")

    elif cmd == "search":
        if len(args) < 2:
            print("错误: 需要提供搜索关键词")
            sys.exit(1)
        keyword = args[1]
        results = search(keyword)
        for r in results:
            print(f"  [{r['match_type']}] {r['name']} ({r['code']})")

    elif cmd == "normalize":
        if len(args) < 2:
            print("错误: 需要提供板块名称")
            sys.exit(1)
        raw = args[1]
        result = fuzzy_match(raw)
        if result:
            print(f"  归一化: {result['name']} ({result['code']}) [{result['match_type']}]")
        else:
            print(f"  无法归一化: {raw}")

    elif cmd == "normalize-all":
        if len(args) < 2:
            print("错误: 需要提供板块名称串")
            sys.exit(1)
        raw = args[1]
        results = normalize(raw)
        for r in results:
            status = "OK" if r["normalized"] else "FAIL"
            print(f"  {status} {r['raw']} -> {r['name']} ({r.get('code', 'None')})")

    else:
        print(f"未知命令: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()