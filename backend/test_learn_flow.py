#!/usr/bin/env python
"""
test_learn_flow.py - 统一学习测试流程

测试学习流程的各个阶段，输出到对应目录。

Usage:
    cd backend
    python test_learn_flow.py --url "https://news.smm.cn/live"
    python test_learn_flow.py --url "https://news.smm.cn/live" --step 3
"""
import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

# 添加 backend 到 path
sys.path.insert(0, str(Path(__file__).parent))

from script.discovery.html_cleaner import clean_html
from script.discovery.list_discovery import discover_list_config, truncate_html_by_news_items
from script.discovery.content_discovery import discover_content_config
from script.discovery.util.html_fetch import (
    fetch_rendered_html,
    DEFAULT_LIST_DELAY_SECONDS,
    DEFAULT_ARTICLE_WAIT,
)
from script.common.datetimeutil import DATETIME_REGEX
from script.discovery.util.find_api import find_api
from script.discovery.util.analyze_api import analyze_api_params, AnalyzeError
from script.discovery.util.map_api_fields import (
    fetch_api_sample,
    discover_api_field_mapping,
)


# 步骤配置
STEPS = {
    1: ("list_original", "crawl4ai 抓取列表页原始 HTML"),
    1.5: ("list_api", "find_api 找 API 候选 + analyze + sample + field_mapping"),
    2: ("list_cleaned", "clean_html 清洗列表页"),
    3: ("list_truncated", "truncate_html_by_news_items 截取列表页"),
    4: ("list_dom_result", "discover_list_config LLM DOM 分析"),
    5: ("article_original", "crawl4ai 抓取文章页原始 HTML"),
    6: ("article_cleaned", "clean_article_html 清洗文章页"),
    7: ("content_config", "discover_content_config LLM 正文配置分析"),
}

# 输出目录
TEST_DIR = Path(__file__).parent.parent / "test"


def get_output_name(url: str) -> str:
    """从 URL 提取输出文件名"""
    # 例如: https://news.smm.cn/live -> news_smm_cn_live
    from urllib.parse import urlparse
    parsed = urlparse(url)
    path = parsed.path.strip("/").replace("/", "_")
    return f"{parsed.netloc.replace('.', '_')}_{path}" if path else parsed.netloc.replace('.', '_')


def load_source_urls(list_result_path: Path) -> dict:
    """从 list_dom_result JSON 加载 article_url"""
    with open(list_result_path, 'r', encoding='utf-8') as f:
        result = json.load(f)
    article = result.get("article", {})
    return article.get("url"), article.get("title")


def step1_crawl_list(url: str, output_dir: Path, name: str, wait_for: str | None = None, delay: float | None = DEFAULT_LIST_DELAY_SECONDS) -> Path:
    """Step 1: crawl4ai 抓取列表页

    默认用固定 delay（DEFAULT_LIST_DELAY_SECONDS）等待 JS 渲染，
    显式传 wait_for 时改用 selector-based wait（风险自负）。
    """
    print(f"[Step 1] crawl4ai 抓取列表页: {url}")
    if wait_for:
        print(f"[Step 1] wait_for: {wait_for}")
    else:
        print(f"[Step 1] delay: {delay}s")
    _, html = asyncio.run(fetch_rendered_html(url, wait_for=wait_for, delay_before_return_html=delay))
    if not html:
        raise RuntimeError(f"抓取失败: {url}")

    output_path = output_dir / f"{name}.html"
    output_dir.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"[Step 1] 已保存: {output_path} ({len(html)} bytes)")
    return output_path


def step2_clean_list(input_path: Path, output_dir: Path, name: str) -> Path:
    """Step 2: clean_html 清洗列表页"""
    print(f"[Step 2] clean_html 清洗列表页")

    with open(input_path, 'r', encoding='utf-8') as f:
        html = f.read()

    result = clean_html(html)

    output_path = output_dir / f"{name}.html"
    output_dir.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(result.html)
    print(f"[Step 2] 已保存: {output_path} ({len(result.html)} bytes), 移除标签: {result.removed_count}")
    return output_path


def step3_truncate_list(input_path: Path, output_dir: Path, name: str) -> Path:
    """Step 3: truncate_html_by_news_items 截取列表页"""
    print(f"[Step 3] truncate_html_by_news_items 截取列表页")

    with open(input_path, 'r', encoding='utf-8') as f:
        html = f.read()

    truncated = truncate_html_by_news_items(html, max_size=200*1024)

    output_path = output_dir / f"{name}.html"
    output_dir.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(truncated)
    print(f"[Step 3] 已保存: {output_path} ({len(truncated)} bytes)")
    return output_path


def step4_discover_list(url: str, input_path: Path, output_dir: Path, name: str, headline: str = "", force_relearn: bool = False) -> Path:
    """Step 4: discover_list_config LLM DOM 分析

    Args:
        headline: 已知文章标题，用于多候选列表块时 LLM 消歧
        force_relearn: True 时跳过 __NEXT_DATA__ 快捷路径，强制 LLM 分析
    """
    print(f"[Step 4] discover_list_config LLM DOM 分析")
    if headline:
        print(f"[Step 4] 使用已知标题消歧: {headline}")
    if force_relearn:
        print(f"[Step 4] force_relearn=True，跳过 __NEXT_DATA__ 快捷路径")

    with open(input_path, 'r', encoding='utf-8') as f:
        html = f.read()

    # input 是已清洗 + 截断后的 HTML，传给 discover_list_config 时需告知跳过内部 clean
    # 否则二次 clean 会把 HTML 压到几乎为空，LLM 无法识别列表块
    result = discover_list_config(url, html, headline=headline, already_cleaned=True, force_relearn=force_relearn)

    output_path = output_dir / f"{name}.json"
    output_dir.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"[Step 4] 已保存: {output_path}")
    return output_path


def step5_crawl_article(article_url: str, output_dir: Path, name: str, wait_for: str | None = None) -> Path:
    """Step 5: crawl4ai 抓取文章页"""
    from urllib.parse import urljoin
    from script.discovery.list_discovery import log as list_log

    # 如果是相对 URL，转为绝对 URL
    if article_url.startswith('/'):
        # 从 list_dom_result 中获取 base URL
        article_url = urljoin("https://news.smm.cn", article_url)

    print(f"[Step 5] crawl4ai 抓取文章页: {article_url}")
    if wait_for:
        print(f"[Step 5] wait_for: {wait_for}")
    _, html = asyncio.run(fetch_rendered_html(article_url, wait_for=wait_for))
    if not html:
        raise RuntimeError(f"抓取失败: {article_url}")

    output_path = output_dir / f"{name}.html"
    output_dir.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"[Step 5] 已保存: {output_path} ({len(html)} bytes)")
    return output_path


def step6_clean_article(input_path: Path, output_dir: Path, name: str) -> Path:
    """Step 6: clean_article_html 清洗文章页"""
    print(f"[Step 6] clean_article_html 清洗文章页")

    with open(input_path, 'r', encoding='utf-8') as f:
        html = f.read()

    from script.discovery.html_cleaner import clean_article_html
    cleaned = clean_article_html(html)

    output_path = output_dir / f"{name}.html"
    output_dir.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(cleaned)
    print(f"[Step 6] 已保存: {output_path} ({len(cleaned)} bytes)")
    return output_path


def step7_discover_content(article_url: str, input_path: Path, output_dir: Path, name: str, headline: str = "") -> Path:
    """Step 7: discover_content_config LLM 正文配置分析"""
    print(f"[Step 7] discover_content_config LLM 正文配置分析")

    with open(input_path, 'r', encoding='utf-8') as f:
        html = f.read()

    result = discover_content_config(article_url, html, headline=headline)

    output_path = output_dir / f"{name}.json"
    output_dir.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"[Step 7] 已保存: {output_path}")
    return output_path


def main():
    parser = argparse.ArgumentParser(description="统一学习测试流程")
    parser.add_argument("--url", required=True, help="数据源 URL，多个用逗号分隔")
    parser.add_argument("--step", type=int, default=1, help="起始步骤 (1-7)")
    parser.add_argument("--title", help="已知文章标题，用于 Step 4 LLM 消歧（多候选列表块时定位）")
    parser.add_argument("--name", help="数据源名称（默认从 URL 派生，用作输出文件名）")
    parser.add_argument("--force-rerun", action="store_true", help="强制重新跑所有 step（即使产物已存在）")
    parser.add_argument(
        "--list-wait",
        default="",
        help="Step 1 抓取列表页的 wait_for 条件（crawl4ai 语法：css:xxx 或 js:() => ...）。留空则用固定 delay {}s".format(DEFAULT_LIST_DELAY_SECONDS),
    )
    parser.add_argument(
        "--list-delay",
        type=float,
        default=DEFAULT_LIST_DELAY_SECONDS,
        help="Step 1 抓取列表页的固定 delay（秒）。仅在 --list-wait 为空时生效",
    )
    parser.add_argument(
        "--article-wait",
        default=DEFAULT_ARTICLE_WAIT,
        help="Step 5 抓取文章页的 wait_for 条件。空字符串表示不等待",
    )
    args = parser.parse_args()

    urls = [u.strip() for u in args.url.split(",")]
    start_step = args.step
    headline = args.title
    force_rerun = args.force_rerun
    list_wait = args.list_wait if args.list_wait else None
    list_delay = args.list_delay if list_wait is None else None
    article_wait = args.article_wait if args.article_wait else None

    print(f"=" * 60)
    print(f"统一学习测试流程")
    print(f"URLs: {urls}")
    print(f"Start Step: {start_step}")
    if headline:
        print(f"Headline: {headline}")
    if list_wait:
        print(f"List wait: {list_wait}")
    else:
        print(f"List delay: {list_delay}s")
    if article_wait:
        print(f"Article wait: {article_wait}")
    print(f"=" * 60)
    print()

    for url in urls:
        # 优先用 --name，否则从 URL 派生
        name = args.name if args.name else get_output_name(url)

        print(f"=" * 60)
        print(f"[处理] {name}")
        print(f"URL: {url}")
        print(f"Start Step: {start_step}")
        print(f"=" * 60)
        print()

        step_paths = {
            1: TEST_DIR / "list_original" / f"{name}.html",
            2: TEST_DIR / "list_cleaned" / f"{name}.html",
            3: TEST_DIR / "list_truncated" / f"{name}.html",
            4: TEST_DIR / "list_dom_result" / f"{name}.json",
            5: TEST_DIR / "article_original" / f"{name}.html",
            6: TEST_DIR / "article_cleaned" / f"{name}.html",
            7: TEST_DIR / "content_config" / f"{name}.json",
        }

        # Step 1: crawl4ai 抓取列表页
        if start_step == 1:
            if force_rerun or not step_paths[1].exists():
                try:
                    step_paths[1] = step1_crawl_list(url, TEST_DIR / "list_original", name, wait_for=list_wait, delay=list_delay)
                except RuntimeError as e:
                    print(f"[ERROR] {e}，跳过")
                    continue
            else:
                print(f"[Step 1] 文件已存在，跳过: {step_paths[1]}")

        # Step 1.5: find_api + analyze + sample + field_mapping (API 流)
        # 如果命中 API 流 → 写 list_dom_result/{name}.json 后跳到 Step 5
        # 如果没命中 → 继续原 HTML 流 Step 2/3/4
        use_api_flow = False
        if start_step <= 1.5 and step_paths[1].exists():
            dom_result = step_paths[4]
            if force_rerun or not dom_result.exists():
                with open(step_paths[1], 'r', encoding='utf-8') as f:
                    list_html = f.read()
                candidates = find_api(list_html, base_url=url, headline=headline)
                if candidates:
                    print(f"[Step 1.5] 找到 {len(candidates)} 个 API 候选，走 API 流")
                    api_dir = TEST_DIR / "list_api"
                    api_dir.mkdir(parents=True, exist_ok=True)
                    # 保存 candidates
                    with open(api_dir / f"{name}_candidates.json", 'w', encoding='utf-8') as f:
                        json.dump(candidates, f, ensure_ascii=False, indent=2)

                    # 重建完整 URL：base + '?' + params（find_api 把 query 拆到 params 里了）
                    from urllib.parse import urlencode
                    cand = candidates[0]
                    base_url = cand['url']
                    full_url = base_url + '?' + urlencode(cand['params'], doseq=True) if cand.get('params') else base_url
                    print(f"[Step 1.5] 选用: {full_url[:100]}")

                    # Step A: analyze_api_params
                    try:
                        analysis = analyze_api_params(full_url)
                        with open(api_dir / f"{name}_params.json", 'w', encoding='utf-8') as f:
                            json.dump(analysis, f, ensure_ascii=False, indent=2)
                        print(f"[Step A] 日期参数: {analysis['date_param']} ({analysis['date_format']}), "
                              f"today={analysis.get('today_items')}, yesterday={analysis.get('yesterday_items')}")
                    except AnalyzeError as e:
                        print(f"[Step A] 失败: {e}，回退到 HTML 流")
                        candidates = []

                    if candidates:
                        # Step B: fetch_api_sample
                        sample = fetch_api_sample(base_url, analysis)
                        with open(api_dir / f"{name}_sample.json", 'w', encoding='utf-8') as f:
                            json.dump({"raw_count": sample['raw_count'],
                                       "today_count": sample['today_count']},
                                      f, ensure_ascii=False, indent=2)
                        print(f"[Step B] 样本: raw={sample['raw_count']}, today={sample['today_count']}")

                        if not sample['items']:
                            print(f"[Step B] 过滤后无当天数据，回退到 HTML 流")
                        else:
                            # Step C: discover_api_field_mapping
                            result = discover_api_field_mapping(
                                sample['items'],
                                api_url=full_url,
                                name=name,
                                analysis=analysis,
                            )
                            dom_result.parent.mkdir(parents=True, exist_ok=True)
                            with open(dom_result, 'w', encoding='utf-8') as f:
                                json.dump(result, f, ensure_ascii=False, indent=2)
                            print(f"[Step C] field_mapping: {result['field_mapping']}")
                            use_api_flow = True
                else:
                    print(f"[Step 1.5] 未找到 API 候选，走 HTML 流")
            else:
                # dom_result 已存在，检查 source_type
                with open(dom_result, 'r', encoding='utf-8') as f:
                    existing = json.load(f)
                if existing.get('source_type') == 'api':
                    use_api_flow = True
                    print(f"[Step 1.5] 检测到已有 API 流结果，复用")

        # Step 2: clean_html 清洗列表页
        if not use_api_flow and start_step <= 2:
            if not step_paths[1].exists():
                print("[ERROR] Step 1 输出不存在，无法继续")
                continue
            if force_rerun or not step_paths[2].exists():
                step_paths[2] = step2_clean_list(step_paths[1], TEST_DIR / "list_cleaned", name)
            else:
                print(f"[Step 2] 文件已存在，跳过: {step_paths[2]}")

        # Step 3: truncate_html_by_news_items 截取列表页
        if not use_api_flow and start_step <= 3:
            if not step_paths[2].exists():
                print("[ERROR] Step 2 输出不存在，无法继续")
                continue
            if force_rerun or not step_paths[3].exists():
                step_paths[3] = step3_truncate_list(step_paths[2], TEST_DIR / "list_truncated", name)
            else:
                print(f"[Step 3] 文件已存在，跳过: {step_paths[3]}")

        # Step 4: discover_list_config LLM DOM 分析
        if not use_api_flow and start_step <= 4:
            if not step_paths[3].exists():
                print("[ERROR] Step 3 输出不存在，无法继续")
                continue
            # Step 4 总是重跑（LLM 结果可能变化，且 --title 会影响消歧）
            step_paths[4] = step4_discover_list(url, step_paths[3], TEST_DIR / "list_dom_result", name, headline=headline, force_relearn=force_rerun)

        # 获取文章 URL
        if start_step <= 4:
            article_url, article_title = load_source_urls(step_paths[4])
            if not article_url:
                print("[ERROR] 无法获取文章 URL，跳过")
                continue
            print(f"[INFO] 文章 URL: {article_url}")
            print(f"[INFO] 文章标题: {article_title}")
        else:
            if not step_paths[4].exists():
                print("[ERROR] Step 4 输出不存在，无法继续")
                continue
            article_url, article_title = load_source_urls(step_paths[4])
            if not article_url:
                print("[ERROR] 无法获取文章 URL，跳过")
                continue

        # Step 5: crawl4ai 抓取文章页
        if start_step <= 5:
            if force_rerun or not step_paths[5].exists():
                try:
                    step_paths[5] = step5_crawl_article(article_url, TEST_DIR / "article_original", name, wait_for=article_wait)
                except RuntimeError as e:
                    print(f"[ERROR] {e}，跳过")
                    continue
            else:
                print(f"[Step 5] 文件已存在，跳过: {step_paths[5]}")

        # Step 6: clean_article_html 清洗文章页
        if start_step <= 6:
            if not step_paths[5].exists():
                print("[ERROR] Step 5 输出不存在，无法继续")
                continue
            if force_rerun or not step_paths[6].exists():
                step_paths[6] = step6_clean_article(step_paths[5], TEST_DIR / "article_cleaned", name)
            else:
                print(f"[Step 6] 文件已存在，跳过: {step_paths[6]}")

        # Step 7: discover_content_config LLM 正文配置分析
        if start_step <= 7:
            if not step_paths[6].exists():
                print("[ERROR] Step 6 输出不存在，无法继续")
                continue
            # Step 7 总是重跑（LLM 结果可能变化）
            step_paths[7] = step7_discover_content(article_url, step_paths[6], TEST_DIR / "content_config", name, headline=article_title)

        print(f"[完成] {name}")
        print()

    print(f"=" * 60)
    print(f"全部完成! 共处理 {len(urls)} 个URL")
    print(f"=" * 60)


if __name__ == "__main__":
    main()
