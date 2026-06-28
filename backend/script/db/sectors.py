"""
sectors.py - 板块数据库管理 (CLI shim)

功能：
  - 从同花顺获取全部板块数据（二级概念/行业板块，共480条）
  - 支持精确匹配、拼音匹配、FTS5全文搜索
  - 零token的板块归一化

实现委托给：
  - sectors_crud.py   - 数据库 CRUD 操作
  - sector_matcher.py - 检索与归一化逻辑

使用：
  python -m db.sectors count
  python -m db.sectors sync [loop=5]
  python -m db.sectors search <关键词>
  python -m db.sectors normalize <板块名>
  python -m db.sectors normalize-all <板块串>
"""

from script.db.sectors_crud import (
    count,
    list_all,
    insert_or_update,
    batch_insert,
    batch_update_keywords,
    sync_from_iwencai as _sync,
)
from script.sector.sector_matcher import search, fuzzy_match, normalize

__all__ = [
    "count",
    "list_all",
    "insert_or_update",
    "batch_insert",
    "batch_update_keywords",
    "sync_from_iwencai",
    "search",
    "fuzzy_match",
    "normalize",
]


def sync_from_iwencai(loop: int = 5) -> dict:
    return _sync(loop=loop)


if __name__ == "__main__":
    import sys

    args = sys.argv[1:]

    if not args:
        print("用法: python -m db.sectors <命令>")
        print("")
        print("命令:")
        print("  count                    - 查看已存储板块数量")
        print("  sync [loop=5]            - 从同花顺同步板块数据")
        print("  search <关键词>          - 搜索板块")
        print("  normalize <板块名>       - 归一化匹配单个板块")
        print("  normalize-all <板块串>  - 归一化多板块（用|分隔）")
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
        for r in search(args[1]):
            print(f"  [{r['match_type']}] {r['name']} ({r['code']})")

    elif cmd == "normalize":
        if len(args) < 2:
            print("错误: 需要提供板块名称")
            sys.exit(1)
        result = fuzzy_match(args[1])
        if result:
            print(f"  归一化: {result['name']} ({result['code']}) [{result['match_type']}]")
        else:
            print(f"  无法归一化: {args[1]}")

    elif cmd == "normalize-all":
        if len(args) < 2:
            print("错误: 需要提供板块名称串")
            sys.exit(1)
        for r in normalize(args[1]):
            status = "OK" if r["normalized"] else "FAIL"
            print(f"  {status} {r['raw']} -> {r['name']} ({r.get('code', 'None')})")

    else:
        print(f"未知命令: {cmd}")
        sys.exit(1)