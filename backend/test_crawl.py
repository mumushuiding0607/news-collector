"""
test_crawl.py - 基于 test/ 目录配置的采集入口

用法：
    python test_crawl.py <url> [--list-only] [--article-only] [--tail N]

行为：
    1. 根据 URL 找到 test/list_dom_result 和 test/content_config 下对应的 JSON 配置
    2. 把配置 upsert 到 source_crawl_configs 表
    3. 调用现有的 list_crawler.main() / article_crawler.main() 跑采集
       （不带 source_name 过滤 → 采集所有源；带 source_name → 只采该源）
    4. 跑完后 tail 日志末尾 N 行打印到 stdout（默认 20）

依赖 test 目录的命名约定（与 test_learn_flow.get_output_name 一致）：
    https://news.smm.cn/live     → news_smm_cn_live.json
    http://www.mydrivers.com     → www_mydrivers_com.json
"""
import argparse
import json
import sys
from datetime import date as _date
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))

from script.bootstrap import *
from script.db.sources_db import upsert_crawl_config

# test/ 目录在项目根，不在 backend/ 下（与 logs/ 同级）
TEST_DIR = Path(APP_ROOT) / "test"


def _tail_log(module: str, n: int) -> None:
    """读 logs/<today>/<module>.log 末尾 n 行打到 stdout（让用户看到结果）"""
    log_file = Path(APP_ROOT) / "logs" / _date.today().isoformat() / f"{module}.log"
    if not log_file.exists():
        print(f"  [日志] 找不到 {log_file}")
        return
    lines = log_file.read_text(encoding="utf-8").splitlines()
    print(f"  [日志] {log_file.name} 末尾 {min(n, len(lines))} 行:")
    for line in lines[-n:]:
        print(f"    {line}")


def name_from_url(url: str) -> str:
    """URL → 测试目录文件名（与 test_learn_flow.get_output_name 一致）"""
    parsed = urlparse(url)
    path = parsed.path.strip("/").replace("/", "_")
    return f"{parsed.netloc.replace('.', '_')}_{path}" if path else parsed.netloc.replace('.', '_')


def load_test_config(url: str) -> tuple[dict, dict]:
    """读 test/list_dom_result 和 test/content_config 下对应的 JSON"""
    name = name_from_url(url)
    list_path = TEST_DIR / "list_dom_result" / f"{name}.json"
    content_path = TEST_DIR / "content_config" / f"{name}.json"

    if not list_path.exists():
        raise FileNotFoundError(f"找不到 list 配置: {list_path}")
    if not content_path.exists():
        raise FileNotFoundError(f"找不到 content 配置: {content_path}")

    with open(list_path, "r", encoding="utf-8") as f:
        list_data = json.load(f)
    with open(content_path, "r", encoding="utf-8") as f:
        content_data = json.load(f)

    return list_data, content_data


def upsert_to_db(url: str, list_data: dict, content_data: dict) -> tuple[int, str]:
    """把 test 配置 upsert 到 source_crawl_configs，返回 (source_id=0, source_name)"""
    # 写 source_crawl_configs
    list_config = list_data.get("list_config") or {}
    content_extract = content_data.get("content_extract") or {}
    # publish_time_pattern 优先 content_data（更具体），其次 list_data
    publish_time_pattern = (
        content_data.get("publish_time_pattern")
        or list_data.get("publish_time_pattern")
        or ""
    )

    upsert_crawl_config(
        url=url,
        name=list_data.get("name"),
        source_type=list_data.get("source_type", "html"),
        list_config=list_config,
        content_extract=json.dumps(content_extract, ensure_ascii=False) if content_extract else None,
        publish_time_pattern=publish_time_pattern,
    )
    print(f"  [DB] source_crawl_configs 已更新")

    source_name = list_data.get("name") or name_from_url(url)
    return 0, source_name


def run_list_crawl(source_name: str | None = None) -> None:
    """调用 list_crawler.main 跑单源（如果不传 source_name 则跑所有源）"""
    from script.crawl.list_crawler import main as list_main
    import asyncio
    asyncio.run(list_main(source_name=source_name))


def run_article_crawl(source_name: str | None = None) -> None:
    """调用 article_crawler.main 跑单源"""
    from script.crawl.article_crawler import main as article_main
    import asyncio
    asyncio.run(article_main(source_name=source_name))


def main():
    parser = argparse.ArgumentParser(description="基于 test/ 配置的采集入口")
    parser.add_argument("url", help="数据源 URL")
    parser.add_argument("--list-only", action="store_true", help="只跑 list_crawler")
    parser.add_argument("--article-only", action="store_true", help="只跑 article_crawler")
    parser.add_argument("--tail", type=int, default=20, help="每步结束后 tail 日志末尾 N 行（默认 20，0 关闭）")
    args = parser.parse_args()

    name = name_from_url(args.url)

    print("=" * 60)
    print(f"基于 test 配置的采集: {name}")
    print(f"URL: {args.url}")
    print("=" * 60)

    # 1. 加载 test 配置
    print(f"\n[1/3] 加载 test 配置: {name}")
    try:
        list_data, content_data = load_test_config(args.url)
    except FileNotFoundError as e:
        print(f"  [ERROR] {e}")
        sys.exit(1)
    print(f"  list_config keys: {list(list_data.get('list_config', {}).keys())}")
    print(f"  content_extract keys: {list(content_data.get('content_extract', {}).keys())}")

    # 2. upsert 到 DB
    print(f"\n[2/3] Upsert 配置到 source_crawl_configs")
    source_id, source_name = upsert_to_db(args.url, list_data, content_data)
    print(f"  source_id={source_id}, source_name={source_name}")

    # 3. 跑 crawler
    if not args.article_only:
        print(f"\n[3/3a] 跑 list_crawler (source_name={source_name!r})")
        print("-" * 60)
        run_list_crawl(source_name=source_name)
        print("-" * 60)
        if args.tail > 0:
            _tail_log("list_crawler", args.tail)

    if not args.list_only:
        print(f"\n[3/3b] 跑 article_crawler (source_name={source_name!r})")
        print("-" * 60)
        run_article_crawl(source_name=source_name)
        print("-" * 60)
        if args.tail > 0:
            _tail_log("article_crawler", args.tail)

    print("\n完成")


if __name__ == "__main__":
    main()
