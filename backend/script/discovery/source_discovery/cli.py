"""
数据源发现模块 - 从异动消息中发现数据源

用法：
    python script/discovery/source_discovery/cli.py <异动消息URL> [--save]

示例：
    python script/discovery/source_discovery/cli.py https://yuanchuang.10jqka.com.cn/mrnxgg_list/index_2.shtml
    python script/discovery/source_discovery/cli.py https://yuanchuang.10jqka.com.cn/mrnxgg_list/index_2.shtml --save
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

import json
import argparse

from script.discovery.source_discovery import discover_sources, discover_and_save
from script.log import log as _log, init_log
from script.common.jsonutil import write_json


def log(msg: str):
    _log("source_discovery", msg)


def main():
    parser = argparse.ArgumentParser(description='从异动消息中发现数据源')
    parser.add_argument('url', help='异动消息列表页 URL')
    parser.add_argument('--save', action='store_true', help='保存发现的数据源到数据库')
    parser.add_argument('--limit', type=int, default=0, help='限制处理的异动数量（0=全部）')
    args = parser.parse_args()

    init_log()
    log(f"开始分析异动消息: {args.url}")

    result = discover_and_save(args.url, save_to_db=args.save) if args.save else discover_sources(args.url)

    if 'error' in result:
        log(f"错误: {result['error']}")
        return 1

    ds = result.get('discovered_sources', [])

    log(f"发现结果:")
    log(f"  异动消息: {result.get('total_anomalies', 0)} 条")
    log(f"  发现数据源: {len(ds)} 个")

    if ds:
        log(f"  数据源列表:")
        for s in ds[:20]:
            log(f"    {s['name']} ({s['count']}次)")

    if args.save:
        log(f"  数据源已保存到数据库")

    # 保存详细结果
    output_file = 'source_discovery_result.json'
    write_json(result, output_file)
    log(f"详细结果已保存到: {output_file}")

    return 0


if __name__ == '__main__':
    sys.exit(main())