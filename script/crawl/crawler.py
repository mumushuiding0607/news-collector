"""
新闻采集主脚本（两步采集法）
Step 1: 从列表页提取所有文章URL+标题（不写库）
Step 2: 逐篇抓取正文 → 提取真实发布时间 → 日期过滤 → 完整正文入库

只采集当天的新闻，非当天或无法确认日期的记录丢弃并报告。
"""
import asyncio
import json
import re
from datetime import datetime, date
from pathlib import Path

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from bs4 import BeautifulSoup
from common.content_filter import get_markdown_generator, get_content_filter, clean_boilerplate_text, extract_clean_content
from common.db import get_conn, init_db, get_all_urls, insert as db_insert, upsert_list_page_article
from common.util import parse_publish_time, is_today, extract_date_from_html


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
    return get_conn()


def log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def _save_article(art: dict, conn) -> bool:
    """保存文章到 primary_sources，返回是否新增成功"""
    return db_insert(art, commit=False)


def _save_list_page_article(art: dict, conn) -> bool:
    """列表页直采模式保存文章（commit=False 由调用方统一 commit）"""
    return upsert_list_page_article(art, commit=False)


def is_article_url(url: str) -> bool:
    # 排除列表页、分类页等非文章 URL
    if url.lower().endswith('.gif'):
        return False
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


# ---------------------------------------------------------------------------
# 列表页直采（用于没有文章链接、或文章页被 anti-bot 拦截的数据源）
# ---------------------------------------------------------------------------

def _html_text(fragment) -> str:
    """从 BS4 element 或原始 HTML 字符串提取纯文本"""
    if fragment is None:
        return ""
    if isinstance(fragment, str):
        return re.sub(r'<[^>]+>', '', fragment).strip()
    return fragment.get_text(separator=' ', strip=True)


def extract_list_page_articles(
    html: str, source_name: str, cfg: dict, list_url: str
) -> list[dict]:
    """
    从列表页 HTML 直接提取文章（title + content + date）。
    适用于生意社等列表页即内容的信源，或文章页全部被 anti-bot 拦截的场景。

    cfg 来源：sources.json 的 listPageExtract 配置
      sourceName        - 必须匹配当前 source name 才生效
      itemSelector      - 每个条目的 CSS 选择器（默认 li）
      titleSelector     - 标题 CSS 选择器（默认 div.pr-news-tit a.blue）
      titleTextSelector - 仅取文本的内部选择器（可选，默认取 titleSelector 元素文本）
      contentSelector   - 正文 CSS 选择器（默认 div.pr-news-txt）
      dateSelector      - 日期 CSS 选择器（默认 div.pr-news-tit span）
      dateExtractMode   - "text" | "attr"（从文本提取 vs 从 attribute 提取）
      linkSelector      - 链接 CSS 选择器（可选）
      linkUrlTemplate   - 链接 URL 模板，如 "https://www.100ppi.com/kx/{href}"
      titleDateRemovePattern - 从标题中去掉日期的正则（可选）
      titleProductOnly  - true 时，只取标题文本中的产品名部分（括号内）【可选】
    """
    if cfg.get("sourceName") != source_name:
        return []

    soup = BeautifulSoup(html, 'html.parser')
    item_sel = cfg.get("itemSelector", "li")
    title_sel = cfg.get("titleSelector", "div.pr-news-tit a.blue")
    content_sel = cfg.get("contentSelector", "div.pr-news-txt")
    date_sel = cfg.get("dateSelector", "div.pr-news-tit span")
    date_mode = cfg.get("dateExtractMode", "text")
    link_sel = cfg.get("linkSelector", "div.pr-news-tit a.blue")
    link_template = cfg.get("linkUrlTemplate", "")
    title_date_pat = cfg.get("titleDateRemovePattern", "")
    title_product_only = cfg.get("titleProductOnly", False)


    articles = []
    for item in soup.select(item_sel):
        # 标题：优先取 link 元素的文本来排除周围噪音
        title_el = item.select_one(title_sel)
        if not title_el:
            fallback_sel = cfg.get("titleSelectorFallback", "")
            if fallback_sel:
                title_el = item.select_one(fallback_sel)
        if not title_el:
            continue
        title_text = title_el.get_text(separator='', strip=True)
        if title_product_only:
            # 只保留括号内产品名（如 [丁酮] → 丁酮）
            m = re.match(r'^\s*\[([^\]]+)\]', title_text)
            if m:
                title_text = m.group(1).strip()
        if len(title_text) <= 2:
            continue
        if title_date_pat:
            title_text = re.sub(title_date_pat, '', title_text).strip()
        title_text = re.sub(r'\s+', ' ', title_text).strip()

        # 日期
        date_str = None
        if date_sel:
            date_el = item.select_one(date_sel)
            if date_el:
                if date_mode == "attr":
                    date_str = date_el.get(date_mode, "") or ""
                else:
                    date_str = date_el.get_text(strip=True)
                    date_str = parse_publish_time(date_str)

        # 正文
        content = ""
        if content_sel:
            content_el = item.select_one(content_sel)
            if content_el:
                content = content_el.get_text(separator=' ', strip=True)
                content = clean_boilerplate_text(content)

        # 链接
        url = ""
        if link_sel and link_template:
            link_el = item.select_one(link_sel)
            if link_el and link_el.get('href'):
                href = link_el.get('href')
                url = link_template.replace("{href}", href)
        elif link_template:
            # 没有 link selector：直接从 item 找 href
            link_el = item.find('a', href=True)
            if link_el:
                href = link_el.get('href')
                url = link_template.replace("{href}", href)

        # 副标题（用正文前200字符）
        subtitle = content[:300] if content else ""

        articles.append({
            "source_name": source_name,
            "title": title_text,
            "url": url,
            "subtitle": subtitle,
            "publish_time": date_str or "",
            "content": content,
        })

    return articles


async def crawl_article(article: dict, crawler, fallback_date: str | None = None) -> dict | str:
    name = article["source_name"]
    url = article["url"]
    title = article["title"]
    subtitle = article["subtitle"]

    run_cfg = CrawlerRunConfig(
        word_count_threshold=50,
        verbose=False,
        delay_before_return_html=2.0,
        markdown_generator=DefaultMarkdownGenerator(
            content_filter=get_content_filter()
        ),
    )
    try:
        result = await crawler.arun(url=url, config=run_cfg)
        if not result.success:
            log(f"  [FAIL] {url}: {result.error_message}")
            return 'no_date'
        html = result.html or ""
        pub_time = extract_date_from_html(html, url=url)

        # 文章页无法提取时间，则用列表页 fallback
        if not pub_time and fallback_date:
            pub_time = fallback_date
            log(f"  [FALLBACK] 使用列表页日期 {pub_time} 代替 article.time")

        if not pub_time:
            log(f"  [WARN] 无法确认日期: {url}")
            return 'no_date'
        if not is_today(pub_time):
            return 'not_today'

        # 使用统一过滤器提取正文（替代原来 hardcode 的 news_info 逻辑）
        content = extract_clean_content(html, base_url=url)
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
    global_max_consecutive = sources_data.get("maxConsecutiveNonToday", 10)
    list_page_extract_cfg = sources_data.get("listPageExtract")
    log(f"Sources loaded: {len(sources)}, crawNumPerSource={global_limit}, maxConsecutiveNonToday={global_max_consecutive}, listPageExtract={"有" if list_page_extract_cfg else "无"}")

    init_db()
    conn = get_db()

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

            phase1_articles = extract_article_links(result.markdown or "", name)
            log(f"  [P1] 找到 {len(phase1_articles)} 个文章链接")

            # 判断是否使用列表页直采模式（没有文章链接，或配置指定该源）
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

            for art in new_articles:
                # crawNumPerSource：成功入库达到上限后停止
                if craw_limit and local_today >= craw_limit:
                    log(f"  [P1] 已达每源成功入库上限 {craw_limit}，停止该源")
                    break

                # 列表页直采模式：content 和 publish_time 已直接提取，跳过 crawl_article
                if use_list_page:
                    total_urls += 1
                    pub_time = art.get("publish_time") or ""
                    if not pub_time:
                        local_no_date += 1
                        if name not in no_date_sources:
                            no_date_sources[name] = 0
                        no_date_sources[name] += 1
                        log(f"  -> {art['title'][:40]}... [SKIP] 无日期")
                        continue
                    if not is_today(pub_time):
                        local_old += 1
                        total_skip_old += 1
                        consecutive_not_today += 1
                        log(f"  -> {art['title'][:40]}... [SKIP] 非当天（连续 {consecutive_not_today}/{max_consec}）")
                        continue
                    consecutive_not_today = 0
                    try:
                        ok = _save_list_page_article(art, conn)
                        if ok:
                            local_today += 1
                            total_today += 1
                            if art["url"]:
                                existing_urls.add(art["url"])
                        else:
                            total_skip_dup += 1
                    except Exception as e:
                        log(f"  [DB ERR] {e}")
                    conn.commit()
                    log(f"  -> {art['title'][:40]}... [OK-LP] {pub_time}")
                    continue

                # 正常文章页模式
                # 连续 max_consecutive_non_today 篇非当天 → 认为该源已无新文，停止
                if consecutive_not_today >= max_consec:
                    log(f"  [P1] 连续 {consecutive_not_today} 篇非当天，已达上限 {max_consec}，停止该源")
                    break

                total_urls += 1
                ret = await crawl_article(art, crawler, fallback_date=art.get("list_date"))

                if ret == 'not_today':
                    local_old += 1
                    total_skip_old += 1
                    consecutive_not_today += 1
                    log(f"  -> {art['title'][:40]}... [SKIP] 非当天（连续 {consecutive_not_today}/{max_consec}）")
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
                consecutive_not_today = 0
                log(f"  -> {fetched['title'][:40]}... [OK] {fetched['publish_time']}")
                try:
                    ok = _save_article(fetched, conn)
                    if ok:
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