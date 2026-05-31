"""
source_manager.py - 数据源配置管理工具

功能：
  1. list    - 列出所有数据源
  2. add     - 添加数据源（自动学习提取模式）
  3. remove  - 删除数据源
  4. learn   - 学习指定数据源的提取模式
  5. learn-all - 学习所有数据源的提取模式

使用：
  python -m config.source_manager list
  python -m config.source_manager add "数据源名称" "列表页URL" [--is-flash]
  python -m config.source_manager remove "数据源名称"
  python -m config.source_manager learn "数据源名称"
  python -m config.source_manager learn-all
"""

import asyncio
import json
import random
import re
import sys
import os
from datetime import datetime
from pathlib import Path

# 添加项目根目录到 sys.path，以便导入 common 模块
BASE_DIR = Path(__file__).parent.parent.resolve()  # script/config/ 的 parent 是 script/
sys.path.insert(0, str(BASE_DIR))  # script/

try:
    from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
    from llm import call_async_raw
    from common.util import parse_publish_time
    from common.log import log as _log
except ImportError as e:
    print(f"导入失败: {e}")
    print("请确保已安装依赖: pip install crawl4ai beautifulsoup4 aiohttp")
    sys.exit(1)

# ==================== 配置路径 ====================
CONFIG_DIR = BASE_DIR.parent / "config"  # script/config/ 的 parent 是 script，script 的 parent 是项目根目录
SOURCES_PATH = CONFIG_DIR / "sources.json"


def log(msg: str):
    _log("source_manager", msg)


# ==================== URL 过滤 ====================

def is_article_url(url: str) -> bool:
    if url.lower().endswith('.gif'):
        return False
    if any(k in url.lower() for k in ['/node/', '/category/', '/topic/', '/channel/', '/list/', '/index', '/page']):
        return False
    digit_segs = re.findall(r'/(\d+)', url)
    if not digit_segs:
        digit_segs = re.findall(r'[-.](\d+)[-.]', url)
    if len(digit_segs) >= 1 and any(ext in url for ext in ['.htm', '.html']):
        return True
    if any(p in url.lower() for p in ['/article/', '/news/', '/info/', '/detail/', '/show/']):
        return True
    return False


# ==================== 列表页解析 ====================

def extract_article_links(markdown: str, source_name: str) -> list[dict]:
    articles = []
    lines = markdown.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        m = re.search(r'\[([^\]]+)\]\((https?://[^\)]+)\)', line)
        if not m:
            i += 1
            continue
        title = m.group(1).strip()
        url = m.group(2).strip()
        if not title or len(title) <= 5 or not url or len(url) <= 10:
            i += 1
            continue
        if not is_article_url(url):
            i += 1
            continue

        date_str = None
        found = parse_publish_time(title)
        if found:
            date_str = found
            title = re.sub(r'\s*\d{4}[-/.]\d{1,2}[-/.]\d{1,2}\s*$', '', title).rstrip()
        title = title.strip().strip('[').strip(']').strip()

        if not date_str:
            after_link = line[m.end():].strip()
            if after_link:
                found = parse_publish_time(after_link)
                if found:
                    date_str = found
        if not date_str:
            for look in range(1, 4):
                if i + look >= len(lines):
                    break
                cand = lines[i + look].strip()
                if re.search(r'\[.+\]\(https?://', cand):
                    continue
                found = parse_publish_time(cand)
                if found:
                    date_str = found
                    break

        articles.append({
            "source_name": source_name,
            "title": title,
            "url": url,
            "publish_time": date_str or "",
        })
        i += 1
    return articles


# ==================== LLM 分析 ====================

def build_analysis_prompt(html: str, source_name: str, url: str) -> str:
    snippet = html[:8000]
    return f"""你是一个专业的HTML解析专家。请分析以下HTML内容，帮我完成两项任务：

【任务1】找出文章正文的精确位置
【任务2】找出文章发布时间的精确位置

数据源名称：{source_name}
文章URL：{url}

HTML内容（前8000字符）：
{json.dumps(snippet, ensure_ascii=False)}

请仔细分析：
1. 文章正文在哪些HTML标签和class/id属性中？正文内容的开始和结束位置有什么特征？周围有哪些噪音元素？
2. 文章发布时间在哪些位置？（meta og:published_time、time[datetime]、class 含 time 的标签、正文附近的日期文本、URL 路径中的日期）
3. 这些时间元素的格式是什么？日期是如何嵌入HTML的？

【任务1-正文提取】请生成一个正则表达式，用于精确提取该数据源的文章正文HTML内容。
正则要求：
- 使用 re.DOTALL 标志，支持跨行匹配
- 匹配结果应该是包含正文内容的HTML片段
- 考虑常见的正文容器标签（article、div、section等）
- 考虑class/id属性中包含的关键词（article、content、post、entry、text等）
- 结果应该足够精确，避免包含噪音元素

【任务2-日期提取】请生成一个正则表达式，用于精确提取文章发布时间。
日期提取要求：
- pattern: 主正则，优先匹配日期字符串（捕获组在日期上）
- fallbackPattern: 更宽松的兜底正则（当主正则无法匹配时使用）
- selector: 结构化配置（CSS选择器 + 提取模式），当正则失败时使用
  - css: CSS选择器，如 "div.time-info, span.publish-time, time[datetime]"
  - mode: "text" 表示取标签文本，"attribute:datetime" 表示取 datetime 属性值
- description: 说明为什么这个正则/选择器能正确提取日期

请按以下JSON格式返回：
{{
    "contentExtract": {{
        "pattern": "正则表达式",
        "description": "正则的简要说明",
        "reason": "为什么这个正则能正确提取正文"
    }},
    "publishTimeExtract": {{
        "pattern": "用于匹配日期字符串的主正则（优先使用）",
        "fallbackPattern": "更宽松的兜底正则",
        "selector": {{
            "css": "CSS选择器",
            "mode": "text|attribute:datetime"
        }},
        "description": "为什么这个正则/选择器能正确提取日期"
    }}
}}
"""


async def call_llm_generate_pattern(html: str, source_name: str, url: str) -> dict | None:
    prompt = build_analysis_prompt(html, source_name, url)
    text_blocks = await call_async_raw(prompt, timeout=60)
    if not text_blocks:
        return None

    combined = "\n".join(text_blocks)
    m = re.search(r'\{[\s\S]*\}', combined)
    if not m:
        return None
    try:
        result = json.loads(m.group())
        if not result.get("contentExtract", {}).get("pattern"):
            return None
        pte = result.get("publishTimeExtract", {})
        if not pte.get("pattern"):
            return None
        return result
    except json.JSONDecodeError:
        return None


# ==================== 正文HTML抓取 ====================

async def crawl_article_html(url: str, crawler) -> str | None:
    try:
        run_cfg = CrawlerRunConfig(
            word_count_threshold=0,
            verbose=False,
            delay_before_return_html=3.0,
        )
        result = await crawler.arun(url=url, config=run_cfg)
        if result.success:
            return result.html
        return None
    except Exception as e:
        log(f"  [WARN] 抓取失败 {url}: {e}")
        return None


# ==================== 选择最优正则 ====================

def select_best_pattern(patterns: list, key: str = "pattern") -> str:
    if not patterns:
        return ""
    if len(patterns) == 1:
        return patterns[0][key]

    keywords = ["article", "content", "post", "entry", "text"]
    for p in patterns:
        pat = p.get(key, "")
        if any(kw in pat.lower() for kw in keywords):
            return pat
    return min(patterns, key=lambda x: len(x.get(key, "")))[key]


# ==================== 数据源管理命令 ====================

def list_sources():
    """列出所有数据源"""
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
    """添加数据源"""
    sources_data = json.loads(SOURCES_PATH.read_text(encoding="utf-8"))
    sources = sources_data.get("sources", [])

    # 检查是否已存在
    for s in sources:
        if s["name"] == name:
            log(f"数据源 '{name}' 已存在")
            return

    # 创建新数据源条目
    new_source = {
        "name": name,
        "is_flash": is_flash,
        "url": url,
    }

    # 添加到列表
    sources.append(new_source)
    sources_data["sources"] = sources
    SOURCES_PATH.write_text(json.dumps(sources_data, indent=2, ensure_ascii=False), encoding="utf-8")
    log(f"已添加数据源：{name}")
    log(f"正在学习提取模式...")

    # 自动学习提取模式
    asyncio.run(learn_pattern(name))


def remove_source(name: str):
    """删除数据源"""
    sources_data = json.loads(SOURCES_PATH.read_text(encoding="utf-8"))
    sources = sources_data.get("sources", [])

    new_sources = [s for s in sources if s["name"] != name]

    if len(new_sources) == len(sources):
        log(f"未找到数据源：{name}")
        return

    sources_data["sources"] = new_sources
    SOURCES_PATH.write_text(json.dumps(sources_data, indent=2, ensure_ascii=False), encoding="utf-8")
    log(f"已删除数据源：{name}")


async def learn_pattern(source_name: str):
    """学习指定数据源的提取模式"""
    sources_data = json.loads(SOURCES_PATH.read_text(encoding="utf-8"))
    sources = sources_data.get("sources", [])

    # 找到目标数据源
    target_source = None
    for s in sources:
        if s["name"] == source_name:
            target_source = s
            break

    if not target_source:
        log(f"未找到数据源：{source_name}")
        return

    name = target_source["name"]
    list_url = target_source["url"]

    log(f"\n{'=' * 60}")
    log(f"学习数据源：{name}")
    log(f"列表页URL：{list_url}")

    # Step 1: 抓取列表页
    async with AsyncWebCrawler(config=BrowserConfig(headless=True)) as crawler:
        run_cfg = CrawlerRunConfig(word_count_threshold=20, verbose=False)
        try:
            result = await crawler.arun(url=list_url, config=run_cfg)
            if not result.success:
                log(f"  [FAIL] 列表页抓取失败：{result.error_message}")
                return
        except Exception as e:
            log(f"  [FAIL] 列表页异常：{e}")
            return

        articles = extract_article_links(result.markdown or "", name)
        log(f"  找到 {len(articles)} 个文章链接")

        if not articles:
            log(f"  [WARN] 该数据源没有找到文章链接")
            return

        # Step 2: 随机选择5篇
        sample_size = min(5, len(articles))
        sampled = random.sample(articles, sample_size)
        log(f"  随机选择 {sample_size} 篇进行分析")

        content_patterns = []
        date_patterns = []
        for i, art in enumerate(sampled):
            log(f"  -> [{i + 1}/{sample_size}] 抓取正文：{art['title'][:40]}...")
            html = await crawl_article_html(art["url"], crawler)
            if not html:
                log(f"     抓取HTML失败，跳过")
                continue

            log(f"     分析HTML内容...")
            pattern_info = await call_llm_generate_pattern(html, name, art["url"])
            if pattern_info:
                ce = pattern_info.get("contentExtract", {})
                if ce.get("pattern"):
                    log(f"     正文正则：{ce['pattern'][:80]}")
                    content_patterns.append(ce)
                pte = pattern_info.get("publishTimeExtract", {})
                if pte.get("pattern"):
                    log(f"     日期正则：{pte['pattern'][:80]}")
                    date_patterns.append(pte)
            else:
                log(f"     LLM生成正则失败")
            await asyncio.sleep(1)

        if not content_patterns:
            log(f"  [FAIL] 未能为 {name} 生成任何正文正则")
            return

        log(f"\n  共获取 {len(content_patterns)} 个正文正则候选，{len(date_patterns)} 个日期正则候选")

        # 选择最优 contentExtract
        final_content_pattern = select_best_pattern(content_patterns, "pattern")

        # 验证正文正则语法
        try:
            re.compile(final_content_pattern)
        except re.error as e:
            log(f"  [WARN] 正文正则语法错误：{e}")
            final_content_pattern = content_patterns[0]["pattern"]

        log(f"\n  最终正文正则：{final_content_pattern}")

        # 选择最优 publishTimeExtract
        final_date_extract = None
        if date_patterns:
            final_date_pattern = select_best_pattern(date_patterns, "pattern")
            try:
                re.compile(final_date_pattern)
            except re.error as e:
                log(f"  [WARN] 日期正则语法错误：{e}")
                final_date_pattern = date_patterns[0]["pattern"]

            final_selector = None
            for dp in date_patterns:
                sel = dp.get("selector")
                if sel and sel.get("css"):
                    final_selector = sel
                    break

            final_date_extract = {
                "pattern": final_date_pattern,
                "fallbackPattern": date_patterns[0].get("fallbackPattern", ""),
                "selector": final_selector,
                "description": date_patterns[0].get("description", "")
            }
            log(f"  最终日期正则：{final_date_pattern}")

        # Step 3: 更新sources.json
        for s in sources_data["sources"]:
            if s["name"] == name:
                s["contentExtract"] = final_content_pattern
                if final_date_extract:
                    s["publishTimeExtract"] = final_date_extract
                break

        SOURCES_PATH.write_text(json.dumps(sources_data, indent=2, ensure_ascii=False), encoding="utf-8")
        log(f"  已更新 sources.json 的 contentExtract 和 publishTimeExtract 字段")

    log(f"\n{'=' * 60}")
    log(f"学习完成：{name}")


async def learn_all():
    """学习所有数据源的提取模式"""
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


# ==================== 主入口 ====================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="数据源配置管理工具")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # list 命令
    subparsers.add_parser("list", help="列出所有数据源")

    # add 命令
    add_parser = subparsers.add_parser("add", help="添加数据源")
    add_parser.add_argument("name", help="数据源名称")
    add_parser.add_argument("url", help="列表页URL")
    add_parser.add_argument("--is-flash", action="store_true", help="是否为Flash新闻")

    # remove 命令
    remove_parser = subparsers.add_parser("remove", help="删除数据源")
    remove_parser.add_argument("name", help="数据源名称")

    # learn 命令
    learn_parser = subparsers.add_parser("learn", help="学习指定数据源的提取模式")
    learn_parser.add_argument("name", help="数据源名称")

    # learn-all 命令
    subparsers.add_parser("learn-all", help="学习所有数据源的提取模式")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    if args.command == "list":
        list_sources()
    elif args.command == "add":
        add_source(args.name, args.url, args.is_flash)
    elif args.command == "remove":
        remove_source(args.name)
    elif args.command == "learn":
        asyncio.run(learn_pattern(args.name))
    elif args.command == "learn-all":
        asyncio.run(learn_all())