"""
db/connection.py - 数据库连接和初始化

重要：
  表结构定义在 db/schema.sql 中，不要在代码中硬编码建表语句。
  使用 init_db() 函数统一初始化所有表（执行 schema.sql）。

优化备注（2026-05-30）：
  - LLM调用全部串行，无需并发优化
  - sync_sector_values.py 很少使用，无需缓存
  - rag/parser.py 每次需重新parse_report（内容会更新），无需缓存
  - db层是性能瓶颈，需加连接池避免每次新建连接

使用：
  from common.db import get_conn, init_db
  conn = get_conn()
  init_db()  # 执行 schema.sql，初始化所有表
"""

import sqlite3
import threading
from pathlib import Path
from queue import Queue, Empty

_BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
DB_PATH = _BASE_DIR / "db" / "primary.db"
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"

# 连接池大小
_POOL_SIZE = 5
_pool: Queue = None
_pool_lock = threading.Lock()


def _init_pool():
    """初始化连接池"""
    global _pool
    if _pool is None:
        with _pool_lock:
            if _pool is None:
                _pool = Queue(maxsize=_POOL_SIZE)
                for _ in range(_POOL_SIZE):
                    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
                    conn.execute("PRAGMA journal_mode=WAL")
                    conn.execute("PRAGMA busy_timeout=30000")
                    _pool.put(conn)


def get_conn() -> sqlite3.Connection:
    """返回连接池中的数据库连接（已启用 WAL 模式）"""
    if _pool is None:
        _init_pool()
    try:
        conn = _pool.get(timeout=5)
    except Empty:
        # 池空则创建临时连接（用完关闭）
        conn = sqlite3.connect(str(DB_PATH))
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=30000")
        return conn
    # 检查连接是否仍然可用
    try:
        conn.execute("SELECT 1")
        return conn
    except Exception:
        # 连接失效，重新创建
        conn = sqlite3.connect(str(DB_PATH))
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=30000")
        return conn


def put_conn(conn: sqlite3.Connection):
    """归还连接到连接池"""
    global _pool
    if conn is None:
        return
    if _pool is None:
        conn.close()
        return
    try:
        _pool.put_nowait(conn)
    except Exception:
        conn.close()


def init_db() -> bool:
    """
    执行 schema.sql，初始化所有表。

    注意：schema.sql 是唯一的表结构定义源，
    所有表结构的修改都应通过修改 schema.sql 完成。

    Returns:
        True: 成功
        False: 失败
    """
    if not SCHEMA_PATH.exists():
        print(f"错误: {SCHEMA_PATH} 不存在")
        return False

    try:
        schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
        conn = sqlite3.connect(str(DB_PATH))
        conn.executescript(schema_sql)
        conn.close()
        return True
    except Exception as e:
        print(f"初始化失败: {e}")
        return False