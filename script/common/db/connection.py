"""
db/connection.py - 数据库连接和初始化

重要：
  表结构定义在 db/schema.sql 中，不要在代码中硬编码建表语句。
  使用 init_db() 函数统一初始化所有表（执行 schema.sql）。

使用：
  from common.db import get_conn, init_db
  conn = get_conn()
  init_db()  # 执行 schema.sql，初始化所有表
"""

import sqlite3
from pathlib import Path

_BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
DB_PATH = _BASE_DIR / "db" / "primary.db"
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


def get_conn() -> sqlite3.Connection:
    """返回已启用 WAL 模式的数据库连接"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


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