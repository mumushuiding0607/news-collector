"""
新闻采集主脚本（两步采集法）
Step 1: 从列表页提取所有文章URL+标题（不写库）
Step 2: 逐篇抓取正文 → 提取真实发布时间 → 日期过滤 → 完整正文入库

只采集当天的新闻，非当天或无法确认日期的记录丢弃并报告。
"""
import asyncio
import json
import re
import sqlite3
from datetime import datetime, date
from pathlib import Path

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
from util import COMBINED_DATE_REGEX, parse_publish_time, is_today, extract_date_from_html


BASE_DIR = Path(__file__).parent.parent
DB_PATH = BASE_DIR / "db" / "primary.db"
SOURCES_PATH = BASE_DIR / "config" / "sources.json"
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)
today = date.today()
today_str = today.strftime("%Y-%m-%d")
log_file = LOG_DIR / f"crawl_{datetime.now().strftime('%Y%m%d')}.log"


def log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = get_db()
    conn.executescript(open(BASE_DIR / "db" / "schema.sql", encoding="utf-8").read())
    conn.commit()
    return conn


def is_article_url(url: str) -> bool:
    # 排除列表页、分类页等非文章 URL
    if any(k in url.lower() for k in ['/node/', '/category/', '/topic/', '/channel/', '/list/', '/index', '/page']):
        return False
    # 有 .htm/.html 且 URL 路径中有数字段 → 文章
    digit_segs = re.findall(r'/(\d+)', url)
    if not digit_segs:
        digit_segs = re.findall(r'[-.](\d+)[-.]', url)  # 如 detail-message-1207--1.html
    if len(digit_segs) >= 1 and any(ext in url for ext in ['.htm', '.html']):
        return True
    # 常见文章路径关键词
    if any(p in url.lower() for p in ['/article/', '/news/', '/info/', '/detail/', '/show/']):
        return True
    return False


def clean_markdown_text(text: str) -> str:
    text = re.sub(r'\*+([^*]+)\*+', r'\1', text)
    text = re.sub(r'__([^_]+)__', r'\1', text)
    text = re.sub(r'_([^_]+)_', r'\1', text)
    text = re.sub(r'~~([^~]+)~~', r'\1', text)
    text = re.sub(r'`([^`]+)`', r'\1', text)
    text = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', text)
    text = re.sub(r'!\[\]\([^)]*\)', '', text)
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def extract_article_links_with_dates(markdown: str, source_name: str) -> list[dict]:
    """从列表页 markdown 中提取文章链接，同时尝试从链接所在行提取日期"""
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

        # 从当前行提取日期（标题内、链接后；或后续行）
        date_str = None
        # 1. 尝试从链接标题内提取（[ 标题 2026-05-27 ](url) 这种格式）
        found = parse_publish_time(title)
        if found:
            date_str = found
            # 从标题中移除日期（只去掉末尾的日期模式，保持标题原名）
            title = re.sub(r'\s*\d{4}[-/.]\d{1,2}[-/.]\d{1,2}\s*$', '', title).rstrip()
        # 清理标题：去除首尾空白、方括号等 markdown 残留
        title = title.strip().strip('[').strip(']').strip()
        # 2. 链接行内链接之后的部分（[text](url) 后面的内容）
        if not date_str:
            after_link = line[m.end():].strip()
            if after_link:
                found = parse_publish_time(after_link)
                if found:
                    date_str = found
        # 3. 链接后面的行
        if not date_str:
            for look in range(3):
                if i + look >= len(lines):
                    break
                cand = lines[i + look].strip()
                if re.search(r'\[.+\]\(https?://', cand):
                    continue
                found = parse_publish_time(cand)
                if found:
                    date_str = found
                    break

        after_link = line[m.end():].strip()
        after_link = clean_markdown_text(after_link)
        subtitle = after_link[:300] if after_link else ""
        if not subtitle:
            para_lines = []
            for j in range(1, 3):
                if i + j >= len(lines):
                    break
                nxt = lines[i + j].strip()
                if not nxt or nxt.startswith('![') or re.search(r'\]\(', nxt):
                    break
                nxt = clean_markdown_text(nxt)
                if nxt:
                    para_lines.append(nxt)
            if para_lines:
                subtitle = para_lines[0][:300]
        articles.append({
            "source_name": source_name,
            "title": title,
            "url": url,
            "subtitle": subtitle,
            "list_date": date_str,
        })
        i += 1
    return articles


def extract_article_links(markdown: str, source_name: str) -> list[dict]:
    return extract_article_links_with_dates(markdown, source_name)


async def crawl_article(article: dict, crawler, fallback_date: str | None = None) -> dict | str:
    name = article["source_name"]
    url = article["url"]
    title = article["title"]
    subtitle = article["subtitle"]

    run_cfg = CrawlerRunConfig(
        word_count_threshold=50,
        verbose=False,
        delay_before_return_html=2.0,
    )
    try:
        result = await crawler.arun(url=url, config=run_cfg)
        if not result.success:
            log(f"  [FAIL] {url}: {result.error_message}")
            return 'no_date'
        html = result.html or ""
        md = result.markdown or ""
        pub_time = extract_date_from_html(html)

        # 文章页无法提取时间，则用列表页 fallback
        if not pub_time and fallback_date:
            pub_time = fallback_date
            log(f"  [FALLBACK] 使用列表页日期 {pub_time} 代替 article.time")

        if not pub_time:
            log(f"  [WARN] 无法确认日期: {url}")
            return 'no_date'
        if not is_today(pub_time):
            return 'not_today'

        info_match = re.search(r'<div\s+class="news_info"[^>]*>([\s\S]*?)(?=<div)', html)
        if info_match:
            info_html = info_match.group(1)
            info_html = re.sub(r'<div\s+class="[^"]*photo[^"]*"[\s\S]*?</div>', '', info_html)
            content = re.sub(r'<[^>]+>', '', info_html)
            content = content.replace('&nbsp;', ' ')
            content = re.sub(r'\s+', ' ', content).strip()
            for pattern in [
                r'^出处：.*?\s+',
                r'如需转载.*?举报',
                r'责任编辑：.*$',
                r'举报',
                r'本文结束.*$',
                r'^【.*?】\s*',
            ]:
                content = re.sub(pattern, '', content, flags=re.DOTALL)
            content = re.sub(r'\n{3,}', '\n\n', content).strip()
        else:
            content = clean_markdown_text(md)
        if len(content) < 200:
            log(f"  [WARN] 正文过短（{len(content)}字）: {url}")
            return 'no_date'
        return {
            "source_name": name,
            "title": title,
            "url": url,
            "subtitle": subtitle,
            "publish_time": pub_time,
            "content": content
        }
    except Exception as e:
        log(f"  [FAIL] {url}: {e}")
        return 'no_date'


async def main():
    log("=" * 60)
    log(f"News crawl start {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"Target date: {today_str}（仅采集当天新闻）")

    sources_data = json.loads(SOURCES_PATH.read_text(encoding="utf-8"))
    sources = sources_data["sources"]
    global_limit = sources_data.get("crawNumPerSource")
    log(f"Sources loaded: {len(sources)}, 全局 crawNumPerSource={global_limit}")

    init_db()
    conn = get_db()

    total_urls = 0
    total_today = 0
    total_skip_old = 0
    total_skip_no_date = 0
    total_skip_dup = 0
    no_date_sources = {}

    existing_urls = set()
    cur = conn.execute("SELECT url FROM primary_sources")
    for row in cur:
        existing_urls.add(row[0])
    log(f"已入库URL: {len(existing_urls)} 个")

    async with AsyncWebCrawler(config=BrowserConfig(headless=True)) as crawler:
        for source in sources:
            name = source["name"]
            list_url = source["url"]
            craw_limit = source.get("crawNumPerSource", global_limit)
            log(f"\n-> Phase1 [List] {name}: {list_url}")

            run_cfg = CrawlerRunConfig(word_count_threshold=20, verbose=False)
            try:
                result = await crawler.arun(url=list_url, config=run_cfg)
                if not result.success:
                    log(f"  [FAIL] list page: {result.error_message}")
                    continue
            except Exception as e:
                log(f"  [FAIL] list page exception: {e}")
                continue

            phase1_articles = extract_article_links(result.markdown or "", name)
            log(f"  [P1] 找到 {len(phase1_articles)} 个文章链接")

            new_articles = [a for a in phase1_articles if a["url"] not in existing_urls]
            log(f"  [P1] 其中 {len(new_articles)} 个未入库")

            if not new_articles:
                continue

            local_today = 0
            local_old = 0
            local_no_date = 0

            for art in new_articles:
                # crawNumPerSource：成功入库达到上限后停止
                if craw_limit and local_today >= craw_limit:
                    log(f"  [P1] 已达每源成功入库上限 {craw_limit}，停止该源")
                    break

                total_urls += 1
                ret = await crawl_article(art, crawler, fallback_date=art.get("list_date"))

                if ret == 'not_today':
                    local_old += 1
                    total_skip_old += 1
                    log(f"  -> {art['title'][:40]}... [SKIP] 非当天")
                    continue
                elif ret == 'no_date':
                    local_no_date += 1
                    total_skip_no_date += 1
                    if name not in no_date_sources:
                        no_date_sources[name] = 0
                    no_date_sources[name] += 1
                    log(f"  -> {art['title'][:40]}... [SKIP] 无法确认日期")
                    continue

                fetched = ret
                log(f"  -> {fetched['title'][:40]}... [OK] {fetched['publish_time']}")
                try:
                    conn.execute(
                        """INSERT OR IGNORE INTO primary_sources
                           (source_name, title, url, subtitle, publish_time,
                            content, status, fetched_at)
                           VALUES (?, ?, ?, ?, ?, ?, 'new',
                                   datetime('now','localtime'))""",
                        (fetched["source_name"], fetched["title"], fetched["url"],
                         fetched["subtitle"], fetched["publish_time"],
                         fetched["content"])
                    )
                    if conn.total_changes > 0:
                        local_today += 1
                        total_today += 1
                        existing_urls.add(fetched["url"])
                    else:
                        total_skip_dup += 1
                except Exception as e:
                    log(f"  [DB ERR] {e}")
                conn.commit()
                await asyncio.sleep(0.3)

            log(f"  [P2] {name} 结果: 当天入库 {local_today}, 非当天 {local_old}, 无法确认日期 {local_no_date}")

    log("\n" + "=" * 60)
    log("采集完成")
    log(f"总URL发现: {total_urls}")
    log(f"当天有效入库: {total_today}")
    log(f"非当天丢弃: {total_skip_old}")
    log(f"URL重复（已入库）: {total_skip_dup}")
    log(f"无法确认日期: {total_skip_no_date}")

    if no_date_sources:
        log("\n无法确认日期的信源（请人工确认日期格式）：")
        for sn, cnt in no_date_sources.items():
            log(f"  - {sn}: {cnt} 篇")

    conn.close()


if __name__ == "__main__":
    asyncio.run(main())