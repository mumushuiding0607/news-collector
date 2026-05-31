"""
list_crawler.py - Step 1: 采集列表页

只从列表页提取标题、发布日期、摘要，content 留空。
不访问文章链接（那是 Step 3 的职责）。

每次执行生成新的 batch_id，crawNumPerSource 控制每源入库数量。
"""
import asyncio
import json
import re
from datetime import datetime, date
from pathlib import Path

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
from bs4 import BeautifulSoup

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from crawl.content.content_filter import clean_boilerplate_text
from common.db import get_conn, init_db, get_all_urls, insert as db_insert, upsert_list_page_article
from common.util import parse_publish_time, is_today


BASE_DIR = Path(__file__).parent.parent.parent.resolve()
DB_PATH = BASE_DIR / "db" / "primary.db"
SOURCES_PATH = BASE_DIR / "config" / "sources.json"
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)
today = date.today()
today_str = today.strftime("%Y-%m-%d")
log_file = LOG_DIR / f"list_crawl_{datetime.now().strftime('%Y%m%d')}.log"


def log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    try:
        print(line, flush=True)
    except UnicodeEncodeError:
        print(line.encode("utf-8", errors="replace").decode("utf-8", errors="replace"), flush=True)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def is_article_url(url: str) -> bool:
    """排除列表页、分类页等非文章 URL"""
    if url.lower().endswith('.gif'):
        return False
    # 排除搜索结果页、分类列表页
    if '?s=' in url or '/category/' in url or '/topic/' in url or '/channel/' in url:
        return False
    if any(k in url.lower() for k in ['/node/', '/list/', '/index']):
        return False
    # /news/ 后面必须跟日期 slug（/2026/05/29/）或具体文章路径才算文章
    # 单纯的 /news/ 或 /news/page/N 是列表页
    news_match = re.search(r'/news(/|$|\?)', url)
    if news_match:
        # /news/ 后面必须是 YYYY/MM/DD/ 才算文章
        has_date_slug = bool(re.search(r'/news/\d{4}/\d{2}/\d{2}/', url))
        has_article_path = bool(re.search(r'/news/\d{4}/\d{2}/\d{2}/[^/]+', url))
        if not has_date_slug and not has_article_path:
            return False
        return True
    # 其他域名下的 /article/、/news/ 等
    if any(p in url.lower() for p in ['/article/', '/info/', '/detail/', '/show/']):
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
        m = re.search(r'\[([^\]]+)\]\((https?://[^\s")]+)\)', line)
        if not m:
            i += 1
            continue
        title = m.group(1).strip()
        url = m.group(2).strip().rstrip('"').rstrip(')')
        if not title or len(title) <= 5 or not url or len(url) <= 10:
            i += 1
            continue
        if not is_article_url(url):
            i += 1
            continue

        # 检测链接文本是否为导航/无关文字，需要从后续行找真正标题
        nav_titles = {
            'view more', 'first page', 'previous page', 'next page', 'last page',
            'read more', 'view all', 'home', 'sign in', 'logout', 'member center',
            'trendforce', 'news logo', 'news',
        }
        is_nav = title.lower() in nav_titles or title.lower().startswith('![')

        article_title = title
        subtitle_candidate = None

        if is_nav:
            # 在后续行找真正的文章标题（## 开头或 ** 包裹）
            for look in range(1, 8):
                if i + look >= len(lines):
                    break
                cand = lines[i + look].strip()
                if cand.startswith('![') or cand.startswith('[ ') or not cand:
                    continue
                # 匹配 ** 包裹的标题，** 可能嵌套在 [News] 等前缀外
                m2 = re.search(r'\*\*(.+?)\*\*', cand)
                if m2:
                    candidate = m2.group(1).strip()
                    # 去掉 [News] 等前缀标记
                    candidate = re.sub(r'^\s*\[News\]\s*', '', candidate, flags=re.IGNORECASE)
                    if len(candidate) > 5:
                        article_title = candidate
                        subtitle_candidate = cand
                        break
                elif cand.startswith('## ') or cand.startswith('# '):
                    candidate = re.sub(r'^#+\s*', '', cand)
                    candidate = re.sub(r'^\*\*(.+?)\*\*$', r'\1', candidate).strip()
                    candidate = re.sub(r'^\s*\[News\]\s*', '', candidate, flags=re.IGNORECASE)
                    if len(candidate) > 5:
                        article_title = candidate
                        subtitle_candidate = cand
                        break

        # 提取日期：优先从 URL slug（/YYYY/MM/DD/），次之从标题/后续行
        date_str = None
        slug_match = re.search(r'/(\d{4}/\d{2}/\d{2})/', url)
        if slug_match:
            date_str = slug_match.group(1).replace('/', '-')

        if not date_str:
            found = parse_publish_time(article_title)
            if found:
                date_str = found
                article_title = re.sub(r'\s*\d{4}[-/.]\d{1,2}[-/.]\d{1,2}\s*$', '', article_title).rstrip()

        if not date_str and subtitle_candidate:
            found = parse_publish_time(subtitle_candidate)
            if found:
                date_str = found

        if not date_str:
            for look in range(1, 4):
                if i + look >= len(lines):
                    break
                cand = lines[i + look].strip()
                if cand.startswith('![') or re.search(r'\[.+\]\(https?://', cand):
                    continue
                found = parse_publish_time(cand)
                if found:
                    date_str = found
                    break

        # 提取摘要
        subtitle = ""
        if is_nav and subtitle_candidate:
            # 标题在 i+look 位置，摘要从 i+look+1 开始往后找内容段落
            for j in range(i + look + 1, i + look + 8):
                if j >= len(lines):
                    break
                nxt = lines[j].strip()
                if not nxt or nxt.startswith('![') or nxt.startswith('[') or nxt.startswith('#'):
                    continue
                nxt = clean_markdown_text(nxt)
                if nxt and len(nxt) > 10:
                    subtitle = nxt[:300]
                    break

        # 导航链接且没找到真正标题则跳过
        if is_nav and not subtitle_candidate:
            i += 1
            continue

        article_title = article_title.strip().strip('[').strip(']').strip()
        articles.append({
            "source_name": source_name,
            "title": article_title,
            "url": url,
            "subtitle": subtitle,
            "list_date": date_str,
        })
        i += 1
    return articles


def extract_list_page_articles(
    html: str, source_name: str, cfg: dict, list_url: str
) -> list[dict]:
    """从列表页 HTML 直接提取文章（title + content + date）。用于列表页即内容的信源。"""
    if cfg.get("sourceName") != source_name:
        return []

    soup = BeautifulSoup(html, 'html.parser')
    item_sel = cfg.get("itemSelector", "li")
    title_sel = cfg.get("titleSelector", "div.pr-news-tit a.blue")
    content_sel = cfg.get("contentSelector", "div.pr-news-txt")
    date_sel = cfg.get("dateSelector", "div.pr-news-tit span")
    date_mode = cfg.get("dateExtractMode", "text")
    title_date_pat = cfg.get("titleDateRemovePattern", "")
    title_product_only = cfg.get("titleProductOnly", False)

    articles = []
    for item in soup.select(item_sel):
        # 1. 提取日期（从 dateSelector）
        date_str = None
        if date_sel:
            date_el = item.select_one(date_sel)
            if date_el:
                if date_mode == "attr":
                    date_str = date_el.get(date_mode, "") or ""
                else:
                    date_str = date_el.get_text(strip=True)
                    date_str = parse_publish_time(date_str)

        # 2. 提取标题
        title_el = item.select_one(title_sel)
        if not title_el:
            fallback_sel = cfg.get("titleSelectorFallback", "")
            if fallback_sel:
                title_el = item.select_one(fallback_sel)
        if not title_el:
            continue

        # 移除日期元素，只保留标题文本
        for date_el in title_el.select(date_sel):
            date_el.decompose()

        title_text = title_el.get_text(separator='', strip=True)

        if title_product_only:
            m = re.match(r'^\s*\[([^\]]+)\]', title_text)
            if m:
                title_text = m.group(1).strip()
        if title_date_pat:
            title_text = re.sub(title_date_pat, '', title_text).strip()
        title_text = re.sub(r'\s+', ' ', title_text).strip()

        if len(title_text) <= 2:
            continue

        # 3. 提取内容
        content = ""
        if content_sel:
            content_el = item.select_one(content_sel)
            if content_el:
                content = content_el.get_text(separator=' ', strip=True)
                content = clean_boilerplate_text(content)

        subtitle = content[:300] if content else ""

        articles.append({
            "source_name": source_name,
            "title": title_text,
            "url": "",  # 列表页直采无链接
            "subtitle": subtitle,
            "publish_time": date_str or "",
            "content": content,
        })

    return articles


async def main():
    log("=" * 60)
    log(f"Step 1 [List Crawl] start {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"Target date: {today_str}")

    sources_data = json.loads(SOURCES_PATH.read_text(encoding="utf-8"))
    sources = sources_data["sources"]
    global_limit = sources_data.get("crawNumPerSource")
    global_max_consecutive = sources_data.get("maxConsecutiveNonToday", 10)
    list_page_extract_cfg = sources_data.get("listPageExtract")
    log(f"Sources loaded: {len(sources)}, crawNumPerSource={global_limit}, maxConsecutiveNonToday={global_max_consecutive}")

    init_db()

    from common.db.connection import get_conn
    conn = get_conn()

    # 为本次运行生成批次号
    from common.db.primary_source import get_next_batch_id
    current_batch_id = get_next_batch_id(conn=conn)

    total_urls = 0
    total_today = 0
    total_skip_old = 0
    total_skip_no_date = 0
    total_skip_dup = 0
    no_date_sources = {}

    existing_urls = get_all_urls()
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

            phase1_articles = extract_article_links_with_dates(result.markdown or "", name)
            log(f"  [P1] 找到 {len(phase1_articles)} 个文章链接")

            lpe_cfg = list_page_extract_cfg
            use_list_page = False
            if lpe_cfg and lpe_cfg.get("sourceName") == name and not phase1_articles:
                use_list_page = True
                log(f"  [P1] 该源无文章链接，使用列表页直采模式")
                list_page_articles = extract_list_page_articles(
                    result.html or "", name, lpe_cfg, list_url
                )
                log(f"  [P1] 列表页直采找到 {len(list_page_articles)} 条")
                new_articles = [
                    a for a in list_page_articles
                    if a["url"] not in existing_urls or not a["url"]
                ]
                log(f"  [P1] 其中 {len(new_articles)} 条未入库")
            else:
                new_articles = [a for a in phase1_articles if a["url"] not in existing_urls]
                log(f"  [P1] 其中 {len(new_articles)} 个未入库")

            if not new_articles:
                continue

            max_consec = global_max_consecutive
            consecutive_not_today = 0

            local_today = 0
            local_old = 0
            local_no_date = 0

            local_processed = 0
            for art in new_articles:
                if craw_limit and local_processed >= craw_limit:
                    log(f"  [P1] 已达每源采集上限 {craw_limit}，停止该源")
                    break
                local_processed += 1

                if consecutive_not_today >= max_consec:
                    log(f"  [P1] 连续 {consecutive_not_today} 篇非当天，已达上限 {max_consec}，停止该源")
                    break

                total_urls += 1
                pub_time = art.get("list_date") or art.get("publish_time") or ""

                if not pub_time:
                    # 无日期：有无文章 URL？
                    # 有 URL → 入库（is_useful=0），news_filter 判断是否有用，article_crawler 从文章页提取日期
                    # 无 URL（如生意社列表页直采）→ 必须有日期，否则跳过
                    if not art.get("url"):
                        local_no_date += 1
                        if name not in no_date_sources:
                            no_date_sources[name] = 0
                        no_date_sources[name] += 1
                        log(f"  -> {art['title'][:40]}... [SKIP] 列表页直采无日期")
                        continue
                    ok = db_insert({
                        "source_name": name,
                        "title": art["title"],
                        "url": art["url"],
                        "subtitle": art.get("subtitle", ""),
                        "publish_time": "",
                        "content": art.get("content", ""),
                        "content_length": len(art.get("content", "") or ""),
                        "batch_id": current_batch_id,
                    }, commit=False, conn=conn)
                    if ok:
                        existing_urls.add(art["url"])
                    conn.commit()
                    log(f"  -> {art['title'][:40]}... [NO-DATE] 已入库，news_filter 判断")
                    continue

                if not is_today(pub_time):
                    local_old += 1
                    total_skip_old += 1
                    consecutive_not_today += 1
                    log(f"  -> {art['title'][:40]}... [SKIP] 非当天 {pub_time}（连续 {consecutive_not_today}/{max_consec}）")
                    continue

                consecutive_not_today = 0

                if use_list_page:
                    ok = upsert_list_page_article({
                        "source_name": name,
                        "title": art["title"],
                        "url": art["url"],
                        "subtitle": art.get("subtitle", ""),
                        "publish_time": pub_time,
                        "content": art.get("content", ""),
                    }, commit=False, batch_id=current_batch_id)
                    if ok:
                        local_today += 1
                        total_today += 1
                        if art["url"]:
                            existing_urls.add(art["url"])
                    else:
                        total_skip_dup += 1
                else:
                    ok = db_insert({
                        "source_name": name,
                        "title": art["title"],
                        "url": art["url"],
                        "subtitle": art.get("subtitle", ""),
                        "publish_time": pub_time,
                        "content": "",
                        "content_length": 0,
                        "batch_id": current_batch_id,
                    }, commit=False, conn=conn)
                    if ok:
                        local_today += 1
                        total_today += 1
                        existing_urls.add(art["url"])
                    else:
                        total_skip_dup += 1
                conn.commit()
                log(f"  -> {art['title'][:40]}... [OK] {pub_time}")
                await asyncio.sleep(0.3)

            log(f"  [P1] {name} 结果: 当天入库 {local_today}, 非当天 {local_old}, 无法确认日期 {local_no_date}, 已采 {local_processed}/{craw_limit or '无上限'}")

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