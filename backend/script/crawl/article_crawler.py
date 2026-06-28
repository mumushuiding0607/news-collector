"""
article_crawler.py - Step 3: 增量采集文章正文

读取 is_useful=1 且 status='new' 的记录（仅 Step 2 判定有用的），
逐篇抓取文章正文，日期过滤，用 content_filter 提取干净正文。
"""
import asyncio
import re
from datetime import date
from pathlib import Path

from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler, BrowserConfig

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from script.discovery.html_cleaner import clean_article_html
from script.bootstrap import *
from script.crawl.crawl_config import get_source_is_flash
from script.crawl.crawl_db import get_useful_uncrawled, mark_article_crawled, delete_article
from script.common.util import extract_date_from_html, is_today
from script.db.sources_db import upsert_crawl_config, get_content_extract_config
from script.db import get_conn
from script.db.sources_db import normalize_url_for_db
from script.db.connection import put_conn
from script.log import log as _log, init_log
from script.common.datetimeutil import now_iso
from script.discovery.util.html_fetch import fetch_article_html

today = date.today()
today_str = today.strftime("%Y-%m-%d")
_MODULE = "article_crawler"

# 跨 source 并发上限：避免一次开太多 tab；同源内部仍严格串行（防反爬）
MAX_SOURCE_CONCURRENCY = 5


def log(msg: str):
    _log(_MODULE, msg)


def _should_skip_article_crawl(content: str = "", publish_time: str = "") -> tuple[bool, str]:
    """
    判断是否应该跳过正文抓取。

    跳过条件（两个必须同时满足）：
    1. 有 content（摘要）
    2. publish_time 包含完整的年月日时分（格式如 2026-06-12 14:30）
    """
    if not content or not publish_time:
        return False, ""

    # 检查时间格式是否完整（至少包含 YYYY-MM-DD HH:MM）
    import re
    if re.search(r'\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}', publish_time):
        return True, "has_content_and_time"

    return False, ""


def _get_content_extract_config(source_name: str) -> dict | None:
    """从数据库获取数据源的 content_extract 配置"""
    return get_content_extract_config(source_name)


def _peek_raw_content_extract(source_name: str) -> str | None:
    """直接读 DB 的 content_extract 列原文（不解析），用于诊断非法 JSON"""
    from script.db.sources_db import get_content_extract_by_name
    return get_content_extract_by_name(source_name)


def _try_publish_time_pattern(source_name: str, html: str) -> str | None:
    """
    显式读 publish_time_pattern 独立列（新配置规则），用正则匹配 HTML。
    命中后调 parse_publish_time 规范化。
    """
    from script.db.sources_db import get_publish_time_extract_by_name
    import re
    pattern = get_publish_time_extract_by_name(source_name)
    if not pattern:
        return None
    try:
        m = re.search(pattern, html, re.DOTALL | re.IGNORECASE)
    except re.error as e:
        log(f"  [TIME-DBG] {source_name}: publish_time_pattern 正则错误: {e}")
        return None
    if not m:
        return None
    # 优先取第一个 group，其次取整段
    try:
        raw = m.group(1) if m.group(1) else m.group(0)
    except (IndexError, AttributeError):
        raw = m.group(0) if m.group(0) else ""
    raw = (raw or "").strip()
    if not raw:
        return None
    from script.common.util import parse_publish_time
    return parse_publish_time(raw)


# 统一正文提取函数
_CHINESE_RE = re.compile(r'[一-鿿]')
_META_KW_RE = re.compile(r'(来源|发布时间|浏览次数|作者|编辑|出处|稿件来源)\s*[:：]')
_DISCLAIMER_RE = re.compile(
    r'^(\(|（)?(投资有风险|股市有风险|入市需谨慎|风险提示|免责条款|免责声明|'
    r'Disclaimer|本文仅供参考|不构成投资建议|据此操作风险自担|'
    r'市场有风险投资需谨慎|证券投资咨询服务提供).*',
    re.IGNORECASE,
)


def _extract_by_selector(html: str, selector: str, remove_selectors: list = None) -> str:
    """使用 CSS 选择器从 HTML 提取正文"""
    if not selector or not html:
        return ""
    soup = BeautifulSoup(html, 'html.parser')
    main_content = soup.select_one(selector)
    if not main_content:
        return ""
    if remove_selectors:
        for sel in remove_selectors:
            for elem in main_content.select(sel):
                elem.decompose()
    text = main_content.get_text(separator='\n', strip=True)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def _extract_content_unified(html: str, base_url: str = "", content_cfg: dict = None) -> str:
    """
    正文提取：CSS selector 优先，fallback 到 clean_article_html。

    1. 有 selector 配置 → _extract_by_selector，结果 <100 字 → fallback
    2. 无配置或 fallback → clean_article_html + _extract_text_from_cleaned + 末尾免责截断
    """
    selector = content_cfg.get("selector") if content_cfg else None
    if selector:
        remove_selectors = content_cfg.get("remove_selectors", [])
        extracted = _extract_by_selector(html, selector, remove_selectors)
        if extracted and len(extracted) >= 100:
            extracted = _strip_trailing_disclaimer(extracted)
            return extracted
        elif extracted:
            log(f"  [SELECTOR] 选择器结果过短({len(extracted)}字)，fallback 到通用提取")

    # 无配置或 selector 失败，统一走 clean_article_html 路径
    cleaned_html = clean_article_html(html)
    content = _extract_text_from_cleaned(cleaned_html)
    content = _strip_trailing_disclaimer(content)
    return content


def _extract_text_from_cleaned(cleaned_html: str) -> str:
    """从 clean_article_html 输出中提取纯文本正文"""
    if not cleaned_html:
        return ""
    soup = BeautifulSoup(cleaned_html, 'html.parser')
    body = soup.find('body') or soup
    text = body.get_text(separator="\n", strip=True)

    # 剔除元信息短行
    lines = text.split("\n")
    kept = []
    for line in lines:
        s = line.strip()
        if not s:
            continue
        if len(s) < 100 and _META_KW_RE.search(s):
            continue
        kept.append(s)
    text = "\n".join(kept)

    # 中文行过滤 + 子串去重
    text = _filter_chinese_text(text)
    return text


def _filter_chinese_text(text: str) -> str:
    """过滤文本：保留中文文字内容（含中文标点），过滤纯英文、URL、纯符号行"""
    if not text:
        return ""
    _WS_RE = re.compile(r'\s+')
    lines = text.split("\n")
    kept = []
    kept_compact = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if not _CHINESE_RE.search(stripped):
            continue
        compact = _WS_RE.sub('', stripped)
        if any(compact in kc for kc in kept_compact):
            continue
        kept.append(stripped)
        kept_compact.append(compact)
    return "\n".join(kept).strip()


def _strip_trailing_disclaimer(text: str) -> str:
    """从文本末尾向前剔除匹配免责声明/风险提示的行"""
    if not text:
        return text
    lines = text.split("\n")
    end = len(lines)
    while end > 0 and _DISCLAIMER_RE.match(lines[end - 1].strip()):
        end -= 1
    if end < len(lines):
        return "\n".join(lines[:end]).strip()
    return text


async def crawl_article(article: dict, crawler) -> dict | str:
    """抓取单篇文章正文，返回 dict（成功）或 str（失败原因）"""
    name = article["source_name"]
    url = article["url"]
    title = article["title"]
    news_id = article["id"]

    # Flash 数据源直接使用 summary
    is_flash = get_source_is_flash(name)
    if is_flash:
        content = article.get("summary") or article.get("title", "")
        return {
            "id": news_id, "source_name": name, "title": title, "url": url,
            "publish_time": article.get("publish_time", ""),
            "content": content, "content_length": len(content),
        }

    if not url:
        return 'no_url'

    # 统一走 fetch_article_html 入口（自动等待 JS 渲染，无需按数据源硬编码）
    try:
        _, html, markdown = await fetch_article_html(
            url,
            return_markdown=True,
            crawler=crawler,
        )

        if not html:
            log(f"  [FAIL] {url}: empty html")
            return 'crawl_failed'

        # 获取数据源的 content_extract 配置
        content_cfg = _get_content_extract_config(name)
        # 新配置规则：content_extract 非法 JSON 时显式打 WARN
        if content_cfg is None:
            raw_ce = _peek_raw_content_extract(name)
            if raw_ce:
                log(f"  [CFG-WARN] {name}: content_extract 非法 JSON ({len(raw_ce)} chars)，已忽略")

        # 保存原始配置（用于正文提取），后续 time_selector 使用可安全 or {}
        _content_cfg_for_extract = content_cfg or {}

        # 提取日期（优先使用 time_selector）
        pub_time = None
        time_selector = _content_cfg_for_extract.get("time_selector")
        if time_selector is None:
            log(f"  [TIME-DBG] {name}: 无 time_selector，跳过第 1 层")
        elif not isinstance(time_selector, str) or not time_selector.strip():
            log(f"  [TIME-DBG] {name}: time_selector 为空/非字符串 ({time_selector!r})")
        else:
            from bs4 import BeautifulSoup
            from script.common.datetimeutil import extract_time_text_from_element
            soup = BeautifulSoup(html, 'html.parser')
            time_el = soup.select_one(time_selector)
            if not time_el:
                log(f"  [TIME-DBG] {name}: time_selector='{time_selector}' 未匹配到元素")
            else:
                time_text = extract_time_text_from_element(time_el)
                from script.common.util import parse_publish_time
                pub_time = parse_publish_time(time_text)
                if pub_time:
                    log(f"  [TIME] 使用 time_selector 提取: {pub_time}")
                else:
                    log(f"  [TIME-DBG] {name}: time_selector 命中但 parse_publish_time 失败: {time_text!r}")

        # 第 2 层：显式读 publish_time_pattern 独立列（新配置规则）
        if not pub_time:
            pub_time = _try_publish_time_pattern(name, html)
            if pub_time:
                log(f"  [TIME] 使用 publish_time_pattern: {pub_time}")

        # 第 3 层：通用提取
        if not pub_time:
            pub_time = extract_date_from_html(html, url=url, source_name=name)
            if pub_time:
                log(f"  [TIME] 使用通用提取: {pub_time}")

        if not pub_time and article.get("publish_time"):
            pub_time = article["publish_time"]
            log(f"  [FALLBACK] 使用列表页日期 {pub_time}")

        if not pub_time:
            log(f"  [WARN] 无法确认日期: {url}")
            return 'no_date'

        # 提取正文（CSS selector 优先，fallback 到 clean_article_html）
        content = _extract_content_unified(html, base_url=url, content_cfg=_content_cfg_for_extract)

        if len(content) == 0:
            log(f"  [WARN] 正文为空（提取失败）: {url}")
            return 'content_too_short'

        return {
            "id": news_id, "source_name": name, "title": title, "url": url,
            "publish_time": pub_time, "content": content, "content_length": len(content),
        }
    except Exception as e:
        log(f"  [FAIL] {url}: {e}")
        return 'crawl_failed'


async def main():
    init_log()
    log("=" * 60)
    log(f"Step 3 [Article Crawl] start {now_iso()}")
    log(f"Target date: {today_str}（仅采集当天新闻）")

    rows = get_useful_uncrawled()
    log(f"待采集文章: {len(rows)} 条")

    if not rows:
        log("没有待采集的文章，退出。")
        return

    # 按 source_name 分桶：跨源并发、源内串行，避免对同一站点并发触发反爬
    buckets: dict[str, list[tuple]] = {}
    for row in rows:
        buckets.setdefault(row[1], []).append(row)
    log(f"按 source 分桶: {len(buckets)} 个源, 跨源并发上限 {MAX_SOURCE_CONCURRENCY}")

    stats = {"ok": 0, "skip_old": 0, "skip_no_date": 0, "skip_short": 0, "skip_crawl_failed": 0}
    stats_lock = asyncio.Lock()  # 同源串行 + 跨源并发，多协程并发更新统计须加锁
    sem = asyncio.Semaphore(MAX_SOURCE_CONCURRENCY)

    async with AsyncWebCrawler(config=BrowserConfig(headless=True)) as crawler:
        await asyncio.gather(*[
            _crawl_source_bucket(source_name, source_rows, crawler, sem, stats, stats_lock)
            for source_name, source_rows in buckets.items()
        ])

    log("\n" + "=" * 60)
    log("采集完成")
    log(f"正文入库: {stats['ok']}")
    log(f"非当天丢弃: {stats['skip_old']}")
    log(f"无法确认日期: {stats['skip_no_date']}")
    log(f"正文过短: {stats['skip_short']}")
    log(f"抓取失败: {stats['skip_crawl_failed']}")
    log("=" * 60)


async def _crawl_source_bucket(source_name: str, source_rows: list[tuple],
                               crawler, sem: asyncio.Semaphore,
                               stats: dict, stats_lock: asyncio.Lock) -> None:
    """串行抓取单个 source 内的全部 row（同源不并发，避免反爬）。"""
    async with sem:
        log(f"\n[BUCKET] {source_name}: {len(source_rows)} 篇")
        for row in source_rows:
            await _crawl_one_row(row, crawler, stats, stats_lock)


async def _crawl_one_row(row: tuple, crawler, stats: dict, stats_lock: asyncio.Lock) -> None:
    """抓一篇 + 落库 + 更新统计（错误处理与日志保持原逻辑）。"""
    news_id, source_name, title, url, summary, publish_time = row
    log(f"\n-> {title[:50]}...")
    log(f"  [SOURCE] {source_name}")

    # 跳过抓取的条件：有摘要 + 完整时间戳
    skip, reason = _should_skip_article_crawl(summary or "", publish_time)
    if skip:
        content = summary or ""
        if content:
            mark_article_crawled(news_id, content, len(content), publish_time)
            log(f"  [SKIP:{reason}] 使用摘要作为正文 ({len(content)}字)")
            async with stats_lock:
                stats["ok"] += 1
        else:
            log(f"  [SKIP:{reason}] 无摘要，删除记录")
            delete_article(news_id)
        return

    ret = await crawl_article({
        "id": news_id, "source_name": source_name, "title": title,
        "url": url, "summary": summary, "publish_time": publish_time,
    }, crawler)

    if ret == 'not_today':
        log(f"  [SKIP] 非当天，删除记录")
        delete_article(news_id)
        async with stats_lock:
            stats["skip_old"] += 1
        return
    if ret == 'no_date':
        log(f"  [SKIP] 无法确认日期")
        delete_article(news_id)
        async with stats_lock:
            stats["skip_no_date"] += 1
        return
    if ret == 'content_too_short':
        log(f"  [SKIP] 正文过短")
        delete_article(news_id)
        async with stats_lock:
            stats["skip_short"] += 1
        return
    if ret == 'crawl_failed':
        log(f"  [SKIP] 抓取失败")
        async with stats_lock:
            stats["skip_crawl_failed"] += 1
        return
    if ret == 'no_url':
        log(f"  [SKIP] 无URL")
        async with stats_lock:
            stats["skip_crawl_failed"] += 1
        return

    fetched = ret
    mark_article_crawled(news_id, fetched["content"], fetched["content_length"], fetched["publish_time"])
    log(f"  [OK] {fetched['publish_time']} ({len(fetched['content'])}字)")
    async with stats_lock:
        stats["ok"] += 1


if __name__ == "__main__":
    asyncio.run(main())