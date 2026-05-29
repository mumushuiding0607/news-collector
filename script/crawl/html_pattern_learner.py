"""
html_pattern_learner.py - 学习数据源正文抓取方式

功能：
  1. 接收一个数据源，抓取新闻列表
  2. 从列表中随机选择5篇，抓取正文HTML
  3. 使用LLM分析每篇HTML，总结正文位置，生成抓取正则
  4. 将正则更新到 sources.json 对应数据源的 contentExtract 字段

前置依赖：
  - .env 中需配置 MINIMAX_API_KEY（API密钥）
  - config/sources.json 中需有数据源配置
  - 需安装：pip install crawl4ai beautifulsoup4 aiohttp

使用：
  # 学习模式：为指定数据源生成/更新正则
  python -m crawl.html_pattern_learner "中国能源网"

  # 测试模式：验证正则是否能正确提取某篇文章的正文
  python -m crawl.html_pattern_learner "中国能源网" --test-url https://cnenergynews.cn/article/2026/0529/xxx.html

  # 不指定数据源则遍历所有数据源（耗时较长）
  python -m crawl.html_pattern_learner

输出：
  - 日志写入 logs/pattern_learn_{date}.log
  - 自动更新 config/sources.json 中对应数据源的 contentExtract 字段
"""

import asyncio
import json
import random
import re
import sys
from datetime import datetime
from pathlib import Path

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig

sys.path.insert(0, str(Path(__file__).parent.parent))
from common.llm_client import call_async_raw
from common.util import parse_publish_time


# ==================== 配置路径 ====================

BASE_DIR = Path(__file__).parent.parent.parent.resolve()
SOURCES_PATH = BASE_DIR / "config" / "sources.json"
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)
log_file = LOG_DIR / f"pattern_learn_{datetime.now().strftime('%Y%m%d')}.log"


def log(msg: str):
    """写入日志到文件和stdout（处理Windows GBK编码问题）"""
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    try:
        print(line, flush=True)
    except UnicodeEncodeError:
        # Windows控制台GBK编码不支持时，使用replace模式
        print(line.encode('gbk', errors='replace').decode('gbk'), flush=True)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(line + "\n")


# ==================== URL 过滤 ====================

def is_article_url(url: str) -> bool:
    """
    判断URL是否为文章页，排除列表页、分类页等非文章URL。

    Args:
        url: 待检查的URL

    Returns:
        True=是文章URL，False=不是文章URL
    """
    if url.lower().endswith('.gif'):
        return False
    # 排除含这些关键词的URL
    if any(k in url.lower() for k in ['/node/', '/category/', '/topic/', '/channel/', '/list/', '/index', '/page']):
        return False
    # 数字路径 + .htm/.html 结尾视为文章
    digit_segs = re.findall(r'/(\d+)', url)
    if not digit_segs:
        digit_segs = re.findall(r'[-.](\d+)[-.]', url)
    if len(digit_segs) >= 1 and any(ext in url for ext in ['.htm', '.html']):
        return True
    # 含文章相关关键词
    if any(p in url.lower() for p in ['/article/', '/news/', '/info/', '/detail/', '/show/']):
        return True
    return False


# ==================== 列表页解析 ====================

def extract_article_links(markdown: str, source_name: str) -> list[dict]:
    """
    从列表页的markdown中提取文章链接和标题。

    算法：
      - 通过正则匹配 [标题](URL) 格式提取链接
      - 在链接所在行及后续行尝试解析日期
      - 日期格式：parse_publish_time 支持多种格式

    Args:
        markdown: 列表页抓取后的markdown内容
        source_name: 数据源名称（用于日志）

    Returns:
        list[dict]，每项包含 source_name/title/url/publish_time
    """
    articles = []
    lines = markdown.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        # 提取 [标题](URL) 格式的链接
        m = re.search(r'\[([^\]]+)\]\((https?://[^\)]+)\)', line)
        if not m:
            i += 1
            continue
        title = m.group(1).strip()
        url = m.group(2).strip()
        # 过滤无效链接
        if not title or len(title) <= 5 or not url or len(url) <= 10:
            i += 1
            continue
        if not is_article_url(url):
            i += 1
            continue

        # 尝试从标题提取日期
        date_str = None
        found = parse_publish_time(title)
        if found:
            date_str = found
            title = re.sub(r'\s*\d{4}[-/.]\d{1,2}[-/.]\d{1,2}\s*$', '', title).rstrip()
        title = title.strip().strip('[').strip(']').strip()

        # 尝试从链接后文本提取日期
        if not date_str:
            after_link = line[m.end():].strip()
            if after_link:
                found = parse_publish_time(after_link)
                if found:
                    date_str = found
        # 尝试从后续行提取日期
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
    """
    构建发送给LLM的HTML分析提示词（同时生成 contentExtract 和 publishTimeExtract）。

    Args:
        html: 文章页原始HTML（前8000字符）
        source_name: 数据源名称
        url: 文章URL

    Returns:
        提示词字符串
    """
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
    """
    调用LLM，根据HTML内容生成 contentExtract 和 publishTimeExtract 正则。

    Args:
        html: 文章页原始HTML
        source_name: 数据源名称
        url: 文章URL

    Returns:
        成功返回 {{contentExtract: {pattern, description, reason}, publishTimeExtract: {pattern, fallbackPattern, selector, description}}} 字典
        失败返回 None
    """
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
        # 验证 contentExtract
        if not result.get("contentExtract", {}).get("pattern"):
            return None
        # 验证 publishTimeExtract
        pte = result.get("publishTimeExtract", {})
        if not pte.get("pattern"):
            return None
        return result
    except json.JSONDecodeError:
        return None


async def call_llm_generate_datapattern(html: str, source_name: str, url: str) -> dict | None:
    """
    调用LLM，专门生成日期提取正则（publishTimeExtract）。

    Args:
        html: 文章页原始HTML
        source_name: 数据源名称
        url: 文章URL

    Returns:
        成功返回 {{pattern, fallbackPattern, selector, description}} 字典
        失败返回 None
    """
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
        pte = result.get("publishTimeExtract", {})
        if not pte.get("pattern"):
            return None
        return pte
    except json.JSONDecodeError:
        return None


# ==================== 正文HTML抓取 ====================

async def crawl_article_html(url: str, crawler) -> str | None:
    """
    抓取单篇文章的原始HTML（不转markdown，直接返回原始HTML）。

    Args:
        url: 文章URL
        crawler: AsyncWebCrawler 实例

    Returns:
        成功返回原始HTML字符串，失败返回None
    """
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


# ==================== 测试模式 ====================

async def test_pattern(source_name: str, test_url: str):
    """
    测试模式：用指定数据源的正则提取单篇文章正文，验证正则效果。

    Args:
        source_name: 数据源名称
        test_url: 要测试的文章URL
    """
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from common.html_parser import extract_by_source, get_pattern

    log(f"\n{'='*60}")
    log(f"测试模式")
    log(f"数据源：{source_name}")
    log(f"测试URL：{test_url}")

    pattern = get_pattern(source_name)
    if not pattern:
        log(f"  [FAIL] 未找到 {source_name} 的 contentExtract 正则")
        log(f"  请先运行 python -m crawl.html_pattern_learner \"{source_name}\" 生成正则")
        return

    log(f"  正则：{pattern}")

    async with AsyncWebCrawler(config=BrowserConfig(headless=True)) as crawler:
        run_cfg = CrawlerRunConfig(
            word_count_threshold=0,
            verbose=False,
            delay_before_return_html=3.0,
        )
        try:
            result = await crawler.arun(url=test_url, config=run_cfg)
            if not result.success:
                log(f"  [FAIL] 抓取失败：{result.error_message}")
                return
        except Exception as e:
            log(f"  [FAIL] 抓取异常：{e}")
            return

        html = result.html or ""
        log(f"  HTML长度：{len(html)} 字符")

        content = extract_by_source(html, source_name, base_url=test_url)
        if not content:
            log(f"  [FAIL] 正则未能提取到正文")
            log(f"  可能原因：正则不匹配该页面结构，请重新学习正则")
            return

        log(f"  [OK] 提取到 {len(content)} 字正文")

        # 提取日期
        from common.util import extract_date_from_html
        pub_time = extract_date_from_html(html, url=test_url, source_name=source_name)
        if pub_time:
            log(f"  [OK] 发布日期：{pub_time}")
        else:
            log(f"  [WARN] 未提取到发布日期")

        log(f"\n{'='*60}")
        log(f"--- 正文内容（前500字）---")
        log(content[:500])
        log(f"\n{'='*60}")
        log(f"--- 正文内容（后500字）---")
        log(content[-500:])
        log(f"\n{'='*60}")
        log(f"--- 结束 ---")

    log(f"\n{'='*60}")
    log("测试完成")


# ==================== 主流程 ====================

def select_best_pattern(patterns: list, key: str = "pattern") -> str:
    """
    从多个候选正则中选择最优的一个。

    Args:
        patterns: 候选正则列表
        key: 要提取的字段名

    Returns:
        最优正则字符串
    """
    if not patterns:
        return ""
    if len(patterns) == 1:
        return patterns[0][key]

    # 偏好包含特定关键词的正则
    keywords = ["article", "content", "post", "entry", "text"]
    for p in patterns:
        pat = p.get(key, "")
        if any(kw in pat.lower() for kw in keywords):
            return pat
    # 取最短的正则（通常更精确）
    return min(patterns, key=lambda x: len(x.get(key, "")))[key]


async def main(source_name: str = None, test_url: str = None):
    """
    主导流程：学习数据源正文抓取正则和发布日期提取正则。

    Args:
        source_name: 可选，指定数据源名称。不指定则遍历所有数据源。

    流程：
      1. 加载 sources.json
      2. 抓取列表页，提取文章链接
      3. 随机选5篇，抓取HTML
      4. 每篇调用LLM生成 contentExtract + publishTimeExtract
      5. 汇总选择最优正则
      6. 更新 sources.json 的 contentExtract 和 publishTimeExtract 字段
    """
    sources_data = json.loads(SOURCES_PATH.read_text(encoding="utf-8"))
    sources = sources_data["sources"]

    # 指定数据源时过滤
    if source_name:
        target_source = None
        for s in sources:
            if s["name"] == source_name:
                target_source = s
                break
        if not target_source:
            log(f"未找到数据源：{source_name}")
            return
        sources = [target_source]

    for source in sources:
        name = source["name"]
        list_url = source["url"]
        log(f"\n{'='*60}")
        log(f"学习数据源：{name}")
        log(f"列表页URL：{list_url}")

        # Step 1: 抓取列表页
        async with AsyncWebCrawler(config=BrowserConfig(headless=True)) as crawler:
            run_cfg = CrawlerRunConfig(word_count_threshold=20, verbose=False)
            try:
                result = await crawler.arun(url=list_url, config=run_cfg)
                if not result.success:
                    log(f"  [FAIL] 列表页抓取失败：{result.error_message}")
                    continue
            except Exception as e:
                log(f"  [FAIL] 列表页异常：{e}")
                continue

            articles = extract_article_links(result.markdown or "", name)
            log(f"  找到 {len(articles)} 个文章链接")

            if not articles:
                log(f"  [WARN] 该数据源没有找到文章链接")
                continue

            # Step 2: 随机选择5篇（不足5篇则全部）
            sample_size = min(5, len(articles))
            sampled = random.sample(articles, sample_size)
            log(f"  随机选择 {sample_size} 篇进行分析")

            content_patterns = []  # contentExtract 候选
            date_patterns = []     # publishTimeExtract 候选
            for i, art in enumerate(sampled):
                log(f"  -> [{i+1}/{sample_size}] 抓取正文：{art['title'][:40]}...")
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
                continue

            # Step 3: 汇总分析，生成最终正则
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
                # 验证日期正则语法
                try:
                    re.compile(final_date_pattern)
                except re.error as e:
                    log(f"  [WARN] 日期正则语法错误：{e}")
                    final_date_pattern = date_patterns[0]["pattern"]

                # 收集 selector 配置（取第一个有效的）
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

            # Step 4: 更新sources.json
            for s in sources_data["sources"]:
                if s["name"] == name:
                    s["contentExtract"] = final_content_pattern
                    if final_date_extract:
                        s["publishTimeExtract"] = final_date_extract
                    break

            SOURCES_PATH.write_text(json.dumps(sources_data, indent=2, ensure_ascii=False), encoding="utf-8")
            log(f"  已更新 sources.json 的 contentExtract 和 publishTimeExtract 字段")

    log(f"\n{'='*60}")
    log("学习完成")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="学习数据源正文抓取正则")
    parser.add_argument("source", nargs="?", help="数据源名称（如：中国能源网）")
    parser.add_argument("--test-url", "-t", help="测试模式：指定要测试的文章URL")
    args = parser.parse_args()

    if args.test_url:
        if not args.source:
            print("测试模式需要指定数据源名称")
            print("用法：python -m crawl.html_pattern_learner \"中国能源网\" --test-url https://...")
            sys.exit(1)
        asyncio.run(test_pattern(args.source, args.test_url))
    elif args.source:
        asyncio.run(main(source_name=args.source))
    else:
        print("用法：")
        print("  学习模式：python -m crawl.html_pattern_learner \"中国能源网\"")
        print("  测试模式：python -m crawl.html_pattern_learner \"中国能源网\" --test-url https://cnenergynews.cn/article/...")
        parser.print_help()