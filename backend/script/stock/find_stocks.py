"""
find_stocks.py - 事件驱动的核心标的发现（CLI入口）

使用：
  python script/stock/find_stocks.py [--dry-run] [--min-score N]
"""

import argparse

from script.log import log as _log, init_log
from script.stock.find_stocks_logic import findStocks


def log(msg: str):
    _log("find_stocks", msg)


def main():
    init_log()

    parser = argparse.ArgumentParser(description="事件驱动的核心标的发现")
    parser.add_argument("--dry-run", action="store_true", help="仅模拟，不写入数据库")
    parser.add_argument("--min-score", type=int, default=6, help="最低评分门槛（默认6）")
    args = parser.parse_args()

    findStocks(dry_run=args.dry_run, min_score=args.min_score)


if __name__ == "__main__":
    main()