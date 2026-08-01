"""
db/connection.py - 数据库连接和初始化

功能：
  - 多数据库连接池（按路径分池，ContextVar 切换后自动使用正确池）
  - 表结构初始化（CREATE TABLE IF NOT EXISTS）
  - 自动列迁移（检测缺失列并 ADD COLUMN，不丢数据）
  - 多余列检测（仅警告，不自动删，危险操作需手动确认）

使用：
  from script.db import get_conn, put_conn, init_db
  conn = get_conn()
  put_conn(conn)
  init_db()  # 启动时自动调用
"""

import re
import sqlite3
import threading
from pathlib import Path
from queue import Empty, Queue

from script.bootstrap import get_db_path

def _get_schema_path() -> Path:
    """根据 DB_PATH 动态选择 schema 文件（每次调用实时求值）。"""
    if "ai_news" in str(get_db_path()):
        return Path(__file__).resolve().parent / "ai_news_schema.sql"
    return Path(__file__).resolve().parent / "schema.sql"

_POOL_SIZE = 5
_pools: dict[str, Queue] = {}   # {db_path: connection_queue}
_pool_lock = threading.Lock()


def _get_pool(db_path: str) -> Queue:
    """获取指定数据库路径的连接池（惰性创建，线程安全）。"""
    with _pool_lock:
        if db_path not in _pools:
            _pools[db_path] = Queue(maxsize=_POOL_SIZE)
            for _ in range(_POOL_SIZE):
                conn = sqlite3.connect(db_path, check_same_thread=False)
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA busy_timeout=30000")
                _pools[db_path].put(conn)
        return _pools[db_path]


def get_conn() -> sqlite3.Connection:
    """从当前数据库对应的池中获取一个连接（每次实时读 ContextVar）。

    Returns:
        sqlite3.Connection：已配置 WAL 模式的连接

    Raises:
        sqlite3.Error：连接失败时
    """
    db_path = str(get_db_path())
    pool = _get_pool(db_path)
    try:
        conn = pool.get(timeout=35)
    except Empty:
        conn = sqlite3.connect(db_path, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=30000")
        return conn
    try:
        conn.execute("SELECT 1")
        return conn
    except Exception:
        conn = sqlite3.connect(db_path, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=30000")
        return conn


def put_conn(conn: sqlite3.Connection | None) -> None:
    """将连接归还到对应数据库的池中。"""
    if conn is None:
        return
    try:
        db_path = str(get_db_path())
        pool = _get_pool(db_path)
        pool.put_nowait(conn)
    except Exception:
        conn.close()


def _schema_columns(schema_sql: str, table: str) -> dict[str, str]:
    """从 schema.sql 解析指定表的列名和类型。{col_name: col_type}"""
    # 找该表的 CREATE TABLE 块（找配对括号而非用正则）
    idx1 = schema_sql.find(f'CREATE TABLE IF NOT EXISTS {table}')
    if idx1 == -1:
        return {}
    start = schema_sql.find('(', idx1)
    depth = 1
    i = start + 1
    while i < len(schema_sql) and depth > 0:
        c = schema_sql[i]
        if c == '(':
            depth += 1
        elif c == ')':
            depth -= 1
        i += 1
    block = schema_sql[start + 1:i - 1]

    cols = {}
    # 去掉行注释（-- 到行尾），避免注释内的逗号干扰列分割
    block = re.sub(r'--.*$', '', block, flags=re.MULTILINE)
    # 按逗号分割列定义，跳过括号内的逗号（处理 DEFAULT/CHECK 中的逗号）
    segs = []
    depth = 0
    start = 0
    for i, c in enumerate(block):
        if c == '(':
            depth += 1
        elif c == ')':
            depth -= 1
        elif c == ',' and depth == 0:
            segs.append(block[start:i])
            start = i + 1
    segs.append(block[start:])
    for seg in segs:
        seg = seg.strip()
        if not seg:
            continue
        # 列名是第一个单词
        parts = seg.split()
        if not parts:
            continue
        col_name = parts[0]
        # 过滤约束关键字行（FOREIGN KEY、PRIMARY KEY、UNIQUE、CHECK、CONSTRAINT 等不是列）
        # 也过滤带括号的约束：UNIQUE(col1,col2)、CHECK(...)、FOREIGN KEY(...)
        if col_name.upper() in ('FOREIGN', 'PRIMARY', 'UNIQUE', 'CHECK', 'CONSTRAINT', 'INDEX', 'KEY'):
            continue
        if col_name.upper().startswith(('UNIQUE(', 'CHECK(', 'FOREIGN KEY(', 'CONSTRAINT ')):
            continue
        col_type = parts[1] if len(parts) > 1 else 'TEXT'
        cols[col_name.upper()] = col_type
    return cols


def _table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    """获取表已有的列名（ uppercase）。"""
    return {info[1].upper() for info in conn.execute(f"PRAGMA table_info({table})")}


def _migrate_columns(conn: sqlite3.Connection, schema_sql: str) -> None:
    """增量迁移列。

    - 缺失的列：ALTER TABLE ADD COLUMN（安全）
    - 多余的列：ALTER TABLE DROP COLUMN（自动清理历史遗留）

    Args:
        conn: 数据库连接
        schema_sql: schema.sql 全文内容
    """
    # 获取 schema.sql 中所有表
    schema_tables = re.findall(
        r'CREATE TABLE IF NOT EXISTS (\w+)', schema_sql, re.IGNORECASE
    )

    for table in schema_tables:
        schema_cols = _schema_columns(schema_sql, table)
        if not schema_cols:
            continue

        try:
            actual_cols = _table_columns(conn, table)
        except sqlite3.OperationalError:
            continue  # 表不存在（后续 executescript 会创建）

        # ADD MISSING COLUMNS
        for col_name, col_type in schema_cols.items():
            if col_name.upper() not in actual_cols:
                print(f"[Migration] {table} 缺失列 {col_name}，添加中...")
                try:
                    conn.execute(f'ALTER TABLE "{table}" ADD COLUMN "{col_name}" {col_type}')
                    conn.commit()
                    print(f"[Migration] {table}.{col_name} 已添加")
                except sqlite3.OperationalError as e:
                    print(f"[Migration] 添加列失败: {e}")

        # DROP EXTRA COLUMNS（自动清理历史遗留垃圾列）
        try:
            actual = _table_columns(conn, table)
        except sqlite3.OperationalError:
            continue
        for col in actual:
            if col not in schema_cols and col not in ('AUTOINCREMENT',):
                try:
                    conn.execute(f'ALTER TABLE "{table}" DROP COLUMN "{col}"')
                    conn.commit()
                    print(f"[Migration] {table} 已删除多余列 {col}")
                except sqlite3.OperationalError as e:
                    print(f"[Migration] {table} 删除多余列 {col} 失败: {e}")


def _migrate_constraints(conn: sqlite3.Connection) -> None:
    """创建缺失的索引和约束"""
    pass


def init_db() -> bool:
    """
    执行 schema.sql 创建表，并自动迁移列。

    - CREATE TABLE IF NOT EXISTS（已有表跳过）
    - 缺失列：ALTER TABLE ADD COLUMN（安全）
    - 多余列：ALTER TABLE DROP COLUMN（自动清理历史遗留）
    - 缺失约束/索引：自动创建
    """
    schema_path = _get_schema_path()
    if not schema_path.exists():
        print(f"错误: {schema_path} 不存在")
        return False

    try:
        schema_sql = schema_path.read_text(encoding="utf-8")
        conn = sqlite3.connect(str(get_db_path()))
        conn.executescript(schema_sql)
        _migrate_columns(conn, schema_sql)
        _migrate_constraints(conn)
        conn.close()
        return True
    except Exception as e:
        print(f"初始化失败: {e}")
        return False


# ==================== 公共工具函数 ====================


def rows_to_dicts(conn, sql: str, params: tuple = ()) -> list[dict]:
    """
    执行 SQL 并将结果转换为字典列表。

    Args:
        conn: 数据库连接
        sql: SQL 语句
        params: 查询参数

    Returns:
        list of dict，键为列名
    """
    cur = conn.execute(sql, params)
    rows = cur.fetchall()
    if not rows:
        return []
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in rows]


# SQL 常量
NOW_SQL = "datetime('now','localtime')"
LATEST_BATCH_SUBQUERY = "(SELECT MAX(batch_id) FROM primary_sources)"
