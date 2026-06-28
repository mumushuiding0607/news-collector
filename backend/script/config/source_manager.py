"""
source_manager.py - 数据源配置管理工具 (CLI shim)

功能：
  1. list    - 列出所有数据源
  2. add     - 添加数据源（自动学习提取模式）
  3. remove  - 删除数据源
  4. learn   - 学习指定数据源的提取模式
  5. learn-all - 学习所有数据源的提取模式

实现委托给：
  - source_learning.py - LLM模式学习

使用：
  python -m config.source_manager list
  python -m config.source_manager add "数据源名称" "列表页URL" [--is-flash]
  python -m config.source_manager remove "数据源名称"
  python -m config.source_manager learn "数据源名称"
  python -m config.source_manager learn-all
"""

import asyncio
import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(BASE_DIR))

from script.config.source_learning import learn_pattern_for_source, learn_all_sources
from script.common.jsonutil import write_json
from script.log import log as _log

CONFIG_DIR = BASE_DIR.parent / "config"
SOURCES_PATH = CONFIG_DIR / "sources.json"


def log(msg: str):
    _log("source_manager", msg)


def list_sources():
    sources_data = json.loads(SOURCES_PATH.read_text(encoding="utf-8"))
    sources = sources_data.get("sources", [])
    if not sources:
        log("没有配置任何数据源")
        return
    log(f"\n共 {len(sources)} 个数据源：")
    log("-" * 60)
    for i, s in enumerate(sources, 1):
        is_flash = " [Flash]" if s.get("is_flash", False) else ""
        has_content = "✓" if s.get("contentExtract") else "✗"
        has_time = "✓" if s.get("publishTimeExtract", {}).get("pattern") else "✗"
        log(f"{i}. {s['name']}{is_flash}")
        log(f"   URL: {s['url']}")
        log(f"   正文提取: {has_content} | 日期提取: {has_time}")
        log("-" * 60)


def add_source(name: str, url: str, is_flash: bool = False):
    sources_data = json.loads(SOURCES_PATH.read_text(encoding="utf-8"))
    sources = sources_data.get("sources", [])
    for s in sources:
        if s["name"] == name:
            log(f"数据源 '{name}' 已存在")
            return
    new_source = {"name": name, "is_flash": is_flash, "url": url}
    sources.append(new_source)
    sources_data["sources"] = sources
    write_json(sources_data, SOURCES_PATH)
    log(f"已添加数据源：{name}")
    log(f"正在学习提取模式...")
    result = asyncio.run(learn_pattern(name))
    if result:
        _apply_learned_patterns(name, result)


def remove_source(name: str):
    sources_data = json.loads(SOURCES_PATH.read_text(encoding="utf-8"))
    sources = sources_data.get("sources", [])
    new_sources = [s for s in sources if s["name"] != name]
    if len(new_sources) == len(sources):
        log(f"未找到数据源：{name}")
        return
    sources_data["sources"] = new_sources
    write_json(sources_data, SOURCES_PATH)
    log(f"已删除数据源：{name}")


async def learn_pattern(source_name: str):
    sources_data = json.loads(SOURCES_PATH.read_text(encoding="utf-8"))
    target_source = next((s for s in sources_data["sources"] if s["name"] == source_name), None)
    if not target_source:
        log(f"未找到数据源：{source_name}")
        return None
    result = await learn_pattern_for_source(source_name, target_source["url"], log)
    if result:
        _apply_learned_patterns(source_name, result)
    return result


async def learn_all():
    sources_data = json.loads(SOURCES_PATH.read_text(encoding="utf-8"))
    sources = sources_data.get("sources", [])
    log(f"\n{'=' * 60}")
    log(f"开始学习所有 {len(sources)} 个数据源")
    for i, source in enumerate(sources, 1):
        log(f"\n[{i}/{len(sources)}] 处理数据源：{source['name']}")
        await learn_pattern(source["name"])
        await asyncio.sleep(2)
    log(f"\n{'=' * 60}")
    log("全部学习完成")


def _apply_learned_patterns(source_name: str, result: dict):
    if not result:
        return
    sources_data = json.loads(SOURCES_PATH.read_text(encoding="utf-8"))
    for s in sources_data["sources"]:
        if s["name"] == source_name:
            if result.get("contentExtract"):
                s["contentExtract"] = result["contentExtract"]
            if result.get("publishTimeExtract"):
                s["publishTimeExtract"] = result["publishTimeExtract"]
            break
    write_json(sources_data, SOURCES_PATH)
    log(f"  已更新 sources.json 的 contentExtract 和 publishTimeExtract 字段")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="数据源配置管理工具")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    add_parser = subparsers.add_parser("add", help="添加数据源")
    add_parser.add_argument("name", help="数据源名称")
    add_parser.add_argument("url", help="列表页URL")
    add_parser.add_argument("--is-flash", action="store_true", help="是否为Flash新闻")

    remove_parser = subparsers.add_parser("remove", help="删除数据源")
    remove_parser.add_argument("name", help="数据源名称")

    learn_parser = subparsers.add_parser("learn", help="学习指定数据源的提取模式")
    learn_parser.add_argument("name", help="数据源名称")

    subparsers.add_parser("learn-all", help="学习所有数据源的提取模式")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    if args.command == "add":
        add_source(args.name, args.url, args.is_flash)
    elif args.command == "remove":
        remove_source(args.name)
    elif args.command == "learn":
        asyncio.run(learn_pattern(args.name))
    elif args.command == "learn-all":
        asyncio.run(learn_all())