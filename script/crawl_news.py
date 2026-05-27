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


BASE_DIR = Path(__file__).parent.parent
DB_PATH = BASE_DIR / "db" / "primary.db"
SOURCES_PATH = BASE_DIR / "config" / "sources.json"
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)
today = date.today()
today_str = today.strftime("%Y-%m-%d")
log_file = LOG_DIR / f"crawl_{datetime.now().strftime('%Y%m%d')}.log"

# 排除非文章 URL（备用）
INVALID_URL_PATTERNS = [
    re.compile(r'\.(?:css|js|jpg|jpeg|png|gif|svg|ico|woff|woff2|ttf|eot|map)'),
    re.compile(r'^(?:javascript:|mailto:|tel:|#)'),
    re.compile(r'comment'),
    re.compile(r'#/'),
    re.compile(r'cnzz|51\.la|umeng|baidu\.com|qcloud'),
]

# 整合后的日期时间正则（覆盖所有常见格式）
COMBINED_DATE_REGEX = re.compile(
    r'(?P<iso>(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})T(\d{1,2}):(\d{2}):(\d{2})(?:\.\d+)?)'          # ISO 8601，允许小数秒
    r'|(?P<full>(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})\s+(\d{1,2}):(\d{2}):(\d{2})(?:\.\d+)?)'      # 带秒，允许小数秒
    r'|(?P<short>(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})\s+(\d{1,2}):(\d{2}))'                       # 带分无秒
    r'|(?P<dateonly>(\d{4})[-/.](\d{1,2})[-/.](\d{1,2}))'                                        # 纯数字日期
    r'|(?P<cn_full>(\d{4})年(\d{1,2})月(\d{1,2})日\s*(\d{1,2}):(\d{2}):(\d{2}))'                  # 中文带秒（可无空格）
    r'|(?P<cn_short>(\d{4})年(\d{1,2})月(\d{1,2})日\s*(\d{1,2}):(\d{2}))'                         # 中文带分（可无空格）
    r'|(?P<cn_dateonly>(\d{4})年(\d{1,2})月(\d{1,2})日)'                                          # 中文纯日期
    r'|(?P<en_date>(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},\s+\d{4})'       # 英文月日年
    r'|(?P<us_date>(\d{1,2})/(\d{1,2})/(\d{4}))'                                                  # 美式月/日/年
)


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
    if any(k in url.lower() for k in ['/node/', '/category/', '/topic/', '/channel/', '/list', '/index', '/page']):
        return False
    digit_segs = re.findall(r'/(\d+)', url)
    if len(digit_segs) >= 2 and any(ext in url for ext in ['.htm', '.html']):
        return True
    if any(p in url.lower() for p in ['/article/', '/news/', '/info/', '/detail/', '/show/']):
        return True
    if len(digit_segs) >= 2 and any(h in url.lower() for h in ['people.com.cn', 'moa.gov.cn', 'csia.net.cn', '100ppi.com', 'smm.cn', 'chinania.org.cn']):
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


def parse_publish_time(text: str) -> str | None:
    """从文本中提取并解析日期时间，使用单正则匹配所有常见格式"""
    for m in COMBINED_DATE_REGEX.finditer(text):
        groups = m.groupdict()
        if groups['iso']:
            dt_str = re.sub(r'\.\d+$', '', groups['iso'])   # 去除小数秒
            try:
                dt = datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%S")
                return dt.strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                continue
        elif groups['full']:
            dt_str = re.sub(r'\.\d+$', '', groups['full'])
            for fmt in ["%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S", "%Y.%m.%d %H:%M:%S"]:
                try:
                    dt = datetime.strptime(dt_str, fmt)
                    return dt.strftime("%Y-%m-%d %H:%M:%S")
                except ValueError:
                    continue
        elif groups['short']:
            dt_str = groups['short']
            for fmt in ["%Y-%m-%d %H:%M", "%Y/%m/%d %H:%M", "%Y.%m.%d %H:%M"]:
                try:
                    dt = datetime.strptime(dt_str, fmt)
                    return dt.strftime("%Y-%m-%d %H:%M:00")
                except ValueError:
                    continue
        elif groups['dateonly']:
            dt_str = groups['dateonly']
            for fmt in ["%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"]:
                try:
                    dt = datetime.strptime(dt_str, fmt)
                    return dt.strftime("%Y-%m-%d 00:00:00")
                except ValueError:
                    continue
        elif groups['cn_full']:
            dt_str = groups['cn_full']
            try:
                dt = datetime.strptime(dt_str, "%Y年%m月%d日 %H:%M:%S")
                return dt.strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                continue
        elif groups['cn_short']:
            dt_str = groups['cn_short']
            try:
                dt = datetime.strptime(dt_str, "%Y年%m月%d日 %H:%M")
                return dt.strftime("%Y-%m-%d %H:%M:00")
            except ValueError:
                continue
        elif groups['cn_dateonly']:
            dt_str = groups['cn_dateonly']
            try:
                dt = datetime.strptime(dt_str, "%Y年%m月%d日")
                return dt.strftime("%Y-%m-%d 00:00:00")
            except ValueError:
                continue
        elif groups['en_date']:
            dt_str = groups['en_date']
            try:
                dt = datetime.strptime(dt_str, "%b %d, %Y")
                return dt.strftime("%Y-%m-%d 00:00:00")
            except ValueError:
                continue
        elif groups['us_date']:
            dt_str = groups['us_date']
            try:
                dt = datetime.strptime(dt_str, "%m/%d/%Y")
                return dt.strftime("%Y-%m-%d 00:00:00")
            except ValueError:
                continue
    return None


def is_today(publish_time_str: str | None) -> bool:
    if not publish_time_str:
        return False
    try:
        pub_date = datetime.strptime(publish_time_str[:10], "%Y-%m-%d").date()
        return pub_date == today
    except (ValueError, TypeError):
        return False


def extract_date_from_html(html: str) -> str | None:
    # 策略1：从 news_bt1_left 提取
    bt1 = re.search(r'<div\s+class="news_bt1_left"[^>]*>([\s\S]*?)</div>', html)
    if bt1:
        pub_time = parse_publish_time(bt1.group(1))
        if pub_time:
            return pub_time
    # 策略2：从 news_info 提取
    info = re.search(r'<div\s+class="news_info"[^>]*>([\s\S]*?)</div>', html)
    if info:
        pub_time = parse_publish_time(info.group(1))
        if pub_time:
            return pub_time
    # 策略3：meta 中的标准时间
    meta_dates = re.findall(r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})', html[:5000])
    for d in meta_dates:
        try:
            dt = datetime.strptime(d, "%Y-%m-%d %H:%M:%S")
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            pass
    # 策略4：datePublished / dateModified
    date_meta = re.search(r'(?:datePublished|dateModified|pubdate)[^>]*content="([^"]+)"', html, re.IGNORECASE)
    if date_meta:
        pub_time = parse_publish_time(date_meta.group(1))
        if pub_time:
            return pub_time
    # 最后兜底：全文本扫描
    return parse_publish_time(html[:8000])


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
        })
        i += 1
    return articles


async def crawl_article(article: dict, crawler) -> dict | str:
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

    sources = json.loads(SOURCES_PATH.read_text(encoding="utf-8"))["sources"]
    log(f"Sources loaded: {len(sources)}")

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
            craw_limit = source.get("crawNumPerSource")
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

            if craw_limit and len(new_articles) > craw_limit:
                log(f"  [P1] 达到每源上限 {craw_limit}，仅处理前 {craw_limit} 篇")
                new_articles = new_articles[:craw_limit]

            local_today = 0
            local_old = 0
            local_no_date = 0

            for art in new_articles:
                total_urls += 1
                ret = await crawl_article(art, crawler)

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