"""
init_db.py - 数据库初始化脚本入口

功能：
  基于 script/common/db/schema.sql 统一管理所有表结构
  提供一键初始化入口

使用：
  python init_db.py              # 一键初始化
  python init_db.py --check-only  # 仅检查不修复

重要：
  初始化逻辑统一在 common/__init__.py 中，此文件只是入口。
  所有表结构定义在 script/common/db/schema.sql 中。
"""

import sys
from pathlib import Path

# 添加 script 目录到 path
_BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_BASE_DIR / "script"))

from common import init_all, check_tables, check_sectors, verify_fts


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="数据库初始化工具")
    parser.add_argument("--force-sync", action="store_true", help="强制重新同步sectors")
    parser.add_argument("--force-repair", action="store_true", help="强制修复FTS5")
    parser.add_argument("--check-only", action="store_true", help="仅检查不修复")
    args = parser.parse_args()

    if args.check_only:
        check_tables()
        check_sectors()
        verify_fts()
    else:
        init_all(force_sync=args.force_sync, force_repair=args.force_repair)