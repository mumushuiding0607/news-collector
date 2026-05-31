"""
common/ - 新闻采集系统公共模块

重要：
  所有表结构定义在 script/common/db/schema.sql 中，是唯一的表结构定义源。
  使用 init_all() 函数统一初始化所有表和同步sectors数据。

模块导出：
  数据库操作：get_conn, insert, get_all_urls 等
  初始化工具：init_all, init_db, check_tables, sync_sectors 等
  配置：LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, CACHE_DIR, get_sources_config, get_source_config
  日志：setup_logger, get_logger, timestamp_print

使用：
  from common import init_all, get_conn, LLM_API_KEY, timestamp_print
"""

import sqlite3
import sys
from pathlib import Path
from datetime import datetime

from .db.connection import get_conn
from .db.primary_source import (get_all_urls, get_unread, insert, upsert_list_page_article,
                                 mark_scored, mark_read, get_unfiltered_batch, mark_useful, get_useful_uncrawled)
from .db.importance import insert as insert_importance, get_recent, get_by_score as get_recent_by_score, get_latest_batch
from .db.sectors import normalize, fuzzy_match, search, sync_from_iwencai, count as sectors_count
from . import config
from . import log
from .config import (
    LLM_API_KEY, LLM_BASE_URL, LLM_MODEL,
    DB_PATH, CACHE_DIR,
    get_sources_config, get_source_config,
)

# ==================== 路径配置 ====================

_SCHEMA_PATH = Path(__file__).resolve().parent / "db" / "schema.sql"


# ==================== 初始化工具函数 ====================

def _log(msg: str):
    """日志输出"""
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def init_db() -> bool:
    """
    执行 schema.sql 初始化所有表。

    Returns:
        True: 成功, False: 失败

    注意：schema.sql 是唯一的表结构定义源。
    """
    if not _SCHEMA_PATH.exists():
        print(f"错误: {_SCHEMA_PATH} 不存在")
        return False

    try:
        schema_sql = _SCHEMA_PATH.read_text(encoding="utf-8")
        conn = get_conn()
        conn.executescript(schema_sql)
        conn.close()
        return True
    except Exception as e:
        print(f"初始化失败: {e}")
        return False


def check_tables() -> bool:
    """
    检查所有表和触发器是否存在。

    Returns:
        True: 所有表存在
        False: 有缺失
    """
    _log("=== 检查数据库表 ===")

    required_tables = ["primary_sources", "importance", "sectors", "sector_indices", "collect_log",
                      "rag_sectors", "rag_stocks", "rag_eliminated", "rag_reports"]
    required_triggers = ["sectors_ai", "sectors_ad", "sectors_au"]

    try:
        conn = get_conn()
        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        triggers = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='trigger'"
        ).fetchall()}
        conn.close()

        fts_tables = ["sectors_fts", "sectors_fts_config", "sectors_fts_data",
                       "sectors_fts_idx", "sectors_fts_docsize"]
        fts_ok = all(f in tables for f in fts_tables)

        missing = []

        for t in required_tables:
            status = "OK" if t in tables else "FAIL"
            _log(f"  [{status}] {t}")
            if t not in tables:
                missing.append(f"TABLE:{t}")

        _log(f"  [{'OK' if fts_ok else 'FAIL'}] sectors_fts (FTS5)")
        if not fts_ok:
            missing.append("TABLE:sectors_fts")

        for t in required_triggers:
            status = "OK" if t in triggers else "FAIL"
            _log(f"  [{status}] trigger {t}")
            if t not in triggers:
                missing.append(f"TRIGGER:{t}")

        if missing:
            _log(f"\n缺少: {missing}")
            return False

        _log("\n所有表检查通过")
        return True

    except Exception as e:
        _log(f"表检查失败: {e}")
        return False


def check_sectors() -> int:
    """检查 sectors 板块数据"""
    _log("=== 检查 sectors 板块数据 ===")

    try:
        conn = get_conn()
        count = conn.execute("SELECT COUNT(*) FROM sectors").fetchone()[0]
        conn.close()
        _log(f"  当前板块数量: {count}")
        return count
    except:
        _log("  sectors 表不存在或查询失败")
        return 0


def sync_sectors(loop: int = 5) -> dict:
    """
    从同花顺同步板块数据。

    Args:
        loop: 循环次数，默认5次获取约500条

    Returns:
        {"status": "success", "added": N, "total": N}
    """
    _log("=== 同步板块数据 ===")

    try:
        before = sectors_count()
        _log(f"  同步前: {before} 条")

        result = sync_from_iwencai(loop=loop)

        _log(f"  同步后: {sectors_count()} 条")
        _log(f"  新增: {result.get('added', 0)} 条")
        return result

    except Exception as e:
        _log(f"同步失败: {e}")
        return {"status": "error", "message": str(e)}


def verify_fts() -> bool:
    """验证 FTS5 虚拟表是否正常"""
    _log("=== 验证 FTS5 ===")

    try:
        conn = get_conn()
        n = conn.execute("SELECT COUNT(*) FROM sectors_fts").fetchone()[0]
        conn.close()
        _log(f"  sectors_fts OK ({n})")
        return True
    except:
        return False


def repair_fts() -> bool:
    """
    修复损坏的 FTS5 虚拟表。
    """
    _log("=== 修复 FTS5 ===")

    try:
        conn = get_conn()

        try:
            sectors_data = conn.execute("SELECT * FROM sectors").fetchall()
            _log(f"  备份: {len(sectors_data)} 条记录")
        except:
            sectors_data = []

        # 删除 FTS5 相关表
        for table in ["sectors_fts_config", "sectors_fts_content", "sectors_fts_data",
                       "sectors_fts_docsize", "sectors_fts_idx", "sectors_fts"]:
            try:
                conn.execute(f"DROP TABLE IF EXISTS {table}")
            except:
                pass

        for trigger in ["sectors_ai", "sectors_ad", "sectors_au"]:
            try:
                conn.execute(f"DROP TRIGGER IF EXISTS {trigger}")
            except:
                pass

        # 重新执行 schema.sql
        schema_sql = _SCHEMA_PATH.read_text(encoding="utf-8")
        conn.executescript(schema_sql)
        _log("  schema.sql 已重新执行")

        # 恢复数据
        if sectors_data:
            for row in sectors_data:
                try:
                    conn.execute("""
                        INSERT OR IGNORE INTO sectors
                        (code, name, name_pinyin_initial, name_pinyin_full, keywords, created_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, row[1:])
                except:
                    pass
            conn.commit()

        conn.close()
        _log("FTS5 修复完成")
        return True

    except Exception as e:
        _log(f"FTS5 修复失败: {e}")
        return False


def init_all(force_sync: bool = False, force_repair: bool = False) -> dict:
    """
    一键初始化所有数据库资源。

    Args:
        force_sync: 强制重新同步 sectors
        force_repair: 强制修复 FTS5

    Returns:
        {"tables_ok": bool, "fts_ok": bool, "sectors_count": int}

    使用：
        from common import init_all
        init_all()
    """
    print("=" * 60)
    print("数据库初始化")
    print("=" * 60)
    _log(f"Schema文件: {_SCHEMA_PATH}")
    print("=" * 60)

    results = {"tables_ok": False, "fts_ok": False, "sectors_count": 0}

    # 1. 检查表
    if not check_tables():
        _log("\n正在执行 schema.sql...")
        if not init_db():
            _log("\n表创建失败")
            return results

    results["tables_ok"] = True

    # 2. 验证 FTS5
    if not verify_fts() or force_repair:
        _log("\n正在修复 FTS5...")
        if not repair_fts():
            _log("\nFTS5 修复失败")
            return results

    results["fts_ok"] = True

    # 3. 检查并同步 sectors
    sectors_cnt = check_sectors()

    if sectors_cnt == 0 or force_sync:
        _log("\n正在同步板块数据...")
        sync_result = sync_sectors(loop=5)
        results["sync_result"] = sync_result
        sectors_cnt = sync_result.get("total", 0)
    else:
        _log(f"\nsectors 数据正常 ({sectors_cnt} 条)")

    results["sectors_count"] = sectors_cnt

    # 结果汇总
    print("\n" + "=" * 60)
    print("初始化结果")
    print("=" * 60)
    print(f"  表结构: {'OK' if results['tables_ok'] else 'FAIL'}")
    print(f"  FTS5: {'OK' if results['fts_ok'] else 'FAIL'}")
    print(f"  sectors: {results['sectors_count']} 条")
    print("=" * 60)

    return results


# ==================== 导出 ====================

__all__ = [
    # 数据库操作
    "get_conn",
    "get_all_urls",
    "get_unread",
    "insert",
    "upsert_list_page_article",
    "mark_scored",
    "mark_read",
    "get_unfiltered_batch",
    "mark_useful",
    "get_useful_uncrawled",
    # importance
    "insert_importance",
    "get_recent",
    "get_recent_by_score",
    "get_latest_batch",
    # sectors
    "normalize",
    "fuzzy_match",
    "search",
    "sync_from_iwencai",
    "sectors_count",
    # 初始化工具
    "init_all",
    "init_db",
    "check_tables",
    "check_sectors",
    "sync_sectors",
    "verify_fts",
    "repair_fts",
]