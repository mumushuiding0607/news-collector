"""
article_crawler.py - Step 3: 增量采集文章正文

读取 is_useful=1 且 content_fetched_at IS NULL 的记录（仅 Step 2 判定有用的），
逐篇抓取文章正文，日期过滤，用 content_filter 提取干净正文。
"""
import asyncio
import json
from datetime import datetime, date
from pathlib import Path

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from crawl.content.content_filter import get_content_filter, extract_clean_content
from common.db import get_conn, init_db, get_useful_uncrawled
from common.db import primary_source as db_ps
from common.util import extract_date_from_html, is_today
from script.crawl.js_render_fixes import build_js_run_cfg


BASE_DIR = Path(__file__).parent.parent.parent.resolve()
SOURCES_PATH = BASE_DIR / "config" / "sources.json"
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)
today = date.today()
today_str = today.strftime("%Y-%m-%d")
log_file = LOG_DIR / f"article_crawl_{datetime.now().strftime('%Y%m%d')}.log"


def log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def _get_content_extract_pattern(source_name: str) -> str | None:
    """从 sources.json 获取指定数据源的 contentExtract 正则，无则返回 None"""
    try:
        sources_data = json.loads(SOURCES_PATH.read_text(encoding="utf-8"))
        for s in sources_data.get("sources", []):
            if s.get("name") == source_name:
                ce = s.get("contentExtract", "")
                return ce if ce else None
    except Exception:
        pass
    return None


def _is_flash_source(source_name: str) -> bool:
    """从 sources.json 判断指定数据源是否为快讯（标题即正文）"""
    try:
        sources_data = json.loads(SOURCES_PATH.read_text(encoding="utf-8"))
        for s in sources_data.get("sources", []):
            if s.get("name") == source_name:
                return bool(s.get("is_flash", False))
    except Exception:
        pass
    return False


def _extract_by_content_pattern(html: str, pattern: str) -> str:
    """使用 contentExtract 正则从 HTML 提取正文，返回提取的原始 HTML 片段"""
    if not pattern or not html:
        return ""
    import re
    try:
        m = re.search(pattern, html, re.DOTALL)
        if m:
            return m.group(1) or ""
    except Exception:
        pass
    return ""


async def crawl_article(article: dict, crawler) -> dict | str:
    """抓取单篇文章正文，返回 dict（成功）或 str（失败原因）"""
    name = article["source_name"]
    url = article["url"]
    title = article["title"]
    news_id = article["id"]

    # 快讯（标题即正文）：从 sources.json 判断
    is_flash = _is_flash_source(name)
    if is_flash:
        content = article.get("subtitle") or article.get("title", "")
        return {
            "id": news_id,
            "source_name": name,
            "title": title,
            "url": url,
            "publish_time": article.get("publish_time", ""),
            "content": content,
            "content_length": len(content),
        }

    if not url:
        return 'no_url'

    # JS 渲染站点使用增强配置
    js_cfg = build_js_run_cfg(name)
    if js_cfg:
        run_cfg = js_cfg
    else:
        run_cfg = CrawlerRunConfig(
            word_count_threshold=50,
            verbose=False,
            delay_before_return_html=5.0,
            markdown_generator=DefaultMarkdownGenerator(
                content_filter=get_content_filter()
            ),
        )
    try:
        result = await crawler.arun(url=url, config=run_cfg)
        if not result.success:
            log(f"  [FAIL] {url}: {result.error_message}")
            return 'crawl_failed'

        html = result.html or ""
        pub_time = extract_date_from_html(html, url=url, source_name=name)

        # 如果文章页无法提取日期，保留原有列表页日期
        if not pub_time and article.get("publish_time"):
            pub_time = article["publish_time"]
            log(f"  [FALLBACK] 使用列表页日期 {pub_time}")

        if not pub_time:
            log(f"  [WARN] 无法确认日期: {url}")
            return 'no_date'

        # 优先使用 sources.json 中该数据源的 contentExtract 正则预提取
        content = ""
        ce_pattern = _get_content_extract_pattern(name)
        if ce_pattern:
            raw_html = _extract_by_content_pattern(html, ce_pattern)
            if raw_html and len(raw_html) >= 100:
                content = extract_clean_content(f"<div>{raw_html}</div>", base_url=url)
                if not content or len(content) < 100:
                    # contentExtract 捕获的 HTML 片段内容太少，尝试直接对完整 HTML 提取
                    content = extract_clean_content(html, base_url=url)
            else:
                content = extract_clean_content(html, base_url=url)
        else:
            content = extract_clean_content(html, base_url=url)

        if len(content) == 0:
            log(f"  [WARN] 正文为空（提取失败）: {url}")
            return 'content_too_short'

        return {
            "id": news_id,
            "source_name": name,
            "title": title,
            "url": url,
            "publish_time": pub_time,
            "content": content,
            "content_length": len(content),
        }
    except Exception as e:
        log(f"  [FAIL] {url}: {e}")
        return 'crawl_failed'


async def main():
    log("=" * 60)
    log(f"Step 3 [Article Crawl] start {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"Target date: {today_str}（仅采集当天新闻）")

    init_db()

    rows = get_useful_uncrawled()
    log(f"待采集文章: {len(rows)} 条")

    if not rows:
        log("没有待采集的文章，退出。")
        return

    total_ok = 0
    total_skip_old = 0
    total_skip_no_date = 0
    total_skip_short = 0
    total_skip_crawl_failed = 0

    async with AsyncWebCrawler(config=BrowserConfig(headless=True)) as crawler:
        for row in rows:
            news_id, source_name, title, url, subtitle, publish_time = row
            log(f"\n-> {title[:40]}...")

            ret = await crawl_article({
                "id": news_id,
                "source_name": source_name,
                "title": title,
                "url": url,
                "subtitle": subtitle,
                "publish_time": publish_time,
            }, crawler)

            if ret == 'not_today':
                total_skip_old += 1
                log(f"  [SKIP] 非当天，删除记录")
                db_ps.delete_by_id(news_id)
                continue
            elif ret == 'no_date':
                total_skip_no_date += 1
                log(f"  [SKIP] 无法确认日期")
                db_ps.delete_by_id(news_id)
                continue
            elif ret == 'content_too_short':
                total_skip_short += 1
                log(f"  [SKIP] 正文过短")
                db_ps.delete_by_id(news_id)
                continue
            elif ret == 'crawl_failed':
                total_skip_crawl_failed += 1
                log(f"  [SKIP] 抓取失败")
                continue
            elif ret == 'no_url':
                total_skip_crawl_failed += 1
                log(f"  [SKIP] 无URL")
                continue

            fetched = ret
            db_ps.update_content(news_id, fetched["content"], fetched["content_length"], fetched["publish_time"])
            total_ok += 1
            log(f"  [OK] {fetched['publish_time']} ({len(fetched['content'])}字)")
            await asyncio.sleep(0.5)

    log("\n" + "=" * 60)
    log("采集完成")
    log(f"正文入库: {total_ok}")
    log(f"非当天丢弃: {total_skip_old}")
    log(f"无法确认日期: {total_skip_no_date}")
    log(f"正文过短: {total_skip_short}")
    log(f"抓取失败: {total_skip_crawl_failed}")


if __name__ == "__main__":
    asyncio.run(main())