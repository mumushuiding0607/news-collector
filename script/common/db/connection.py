"""
db/connection.py - 数据库连接和初始化

提供:
  - get_conn(): 返回已配置 WAL 模式的连接
  - init_db(): 执行 schema.sql 初始化所有表
"""

import sqlite3
from pathlib import Path

_BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = _BASE_DIR / "db" / "primary.db"
SCHEMA_PATH = _BASE_DIR / "db" / "schema.sql"


def get_conn() -> sqlite3.Connection:
    """返回已启用 WAL 模式的数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db() -> sqlite3.Connection:
    """执行 schema.sql，初始化所有表"""
    conn = get_conn()
    conn.executescript(open(SCHEMA_PATH, encoding="utf-8").read())
    conn.commit()
    return conn