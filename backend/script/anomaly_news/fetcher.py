"""
anomaly_news/fetcher.py - 异动消息采集

抓取异动消息页面，解析列表，提取数据源，保存到数据库。
调用 script.db.anomaly_news 的 CRUD，不自行操作数据库。
"""
import asyncio
import re
from dataclasses import dataclass
from urllib.parse import urljoin

from script.log import log as _log, init_log
from script.db.anomaly_news import batch_save_anomaly_news, get_anomaly_news_for_content_crawl, update_anomaly_content
from script.common.datetimeutil import now_iso


def log(msg: str):
    _log("anomaly_fetcher", msg)


@dataclass
class AnomalyInfo:
    """单条异动消息"""
    title: str = ""       # 标题
    url: str = ""         # 文章链接
    time: str = ""        # 发布时间
    source_name: str = "" # 数据源名称


# 来源标注正则：据XXXX报道、据XXXX讯、来源：XXXX、XXXX6月11日电 等
_SOURCE_ANNOTATION_RE = re.compile(
    r'来源：([\u4e00-\u9fa5]+)|据([\u4e00-\u9fa5]*(?:社|报|网|台|讯|闻|经|济|日|晚|周|月))(?:\d{1,2}月\d{1,2}日|\d{4}年\d{1,2}月\d{1,2}日)?(?:报道|讯|电)|据([\u4e00-\u9fa5]*(?:社|报|网|台|讯|闻|经|济|日|晚|周|月))(?=，)|据([\u4e00-\u9fa5]*(?:社|报|网|台|讯|闻|经|济|日|晚|周|月))$|([\u4e00-\u9fa5]+)\d{1,2}月\d{1,2}日电',
    re.IGNORECASE,
)


def extract_source_name(title: str) -> str:
    """从异动标题中提取数据源名称"""
    m = _SOURCE_ANNOTATION_RE.search(title)
    if m:
        return (m.group(1) or m.group(2) or m.group(3) or m.group(4) or m.group(5) or '').strip()
    return ''


def parse_list_html(html: str, base_url: str = "") -> list[AnomalyInfo]:
    """解析异动消息列表 HTML"""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, 'html.parser')
    anomalies = []

    for item in soup.find_all('a', class_='news-link'):
        info = AnomalyInfo()
        info.url = item.get('href', '')
        if info.url and not info.url.startswith(('http://', 'https://')):
            info.url = urljoin(base_url, info.url)
        info.title = item.get('title', '') or item.get_text(strip=True)

        # 优先从同级 <span> 提取时间，如「06月17日 16:03」
        span = item.find_next_sibling('span')
        if span:
            m = re.search(r'(\d{2})月(\d{2})日 (\d{2}):(\d{2})', span.get_text())
            if m:
                year_match = re.search(r'/(\d{4})/', info.url)
                year = year_match.group(1) if year_match else "2026"
                info.time = f"{year}-{m.group(1)}-{m.group(2)} {m.group(3)}:{m.group(4)}"
        # 其次从 URL 中的日期 path 提取，如 /20260617/
        if not info.time:
            time_match = re.search(r'/(\d{8})/', info.url)
            if time_match:
                t = time_match.group(1)
                info.time = f"{t[:4]}-{t[4:6]}-{t[6:8]}"

        if info.title and info.url:
            anomalies.append(info)

    return anomalies


def discover_sources(url: str) -> dict:
    """
    从异动消息页面发现数据源（不保存）。

    Returns:
        {total_anomalies, anomalies, discovered_sources}
    """
    init_log()
    log(f"开始分析: {url}")

    from script.discovery.raw_fetch import fetch_raw_html
    html = fetch_raw_html(url)
    if not html:
        return {'error': '无法获取页面', 'url': url}

    anomalies = parse_list_html(html, url)
    log(f"解析到 {len(anomalies)} 条异动消息，提取数据源...")

    for i, a in enumerate(anomalies, 1):
        a.source_name = extract_source_name(a.title)
        source_info = f"[{a.source_name}]" if a.source_name else "[无数据源]"
        log(f"  [{i:02d}] {a.title[:35]}... {source_info}")

    # 统计每个数据源
    source_map = {}
    for a in anomalies:
        name = a.source_name or '未知'
        if name in source_map:
            source_map[name]['count'] += 1
            source_map[name]['articles'].append(a.title[:30])
        else:
            source_map[name] = {'count': 1, 'articles': [a.title[:30]]}

    sorted_sources = sorted(source_map.items(), key=lambda x: -x[1]['count'])
    log(f"\n发现数据源 {len(sorted_sources)} 个:")
    for name, info in sorted_sources:
        log(f"  - {name}: {info['count']}次")

    return {
        'total_anomalies': len(anomalies),
        'anomalies': [
            {'title': a.title, 'url': a.url, 'time': a.time, 'source_name': a.source_name}
            for a in anomalies
        ],
        'discovered_sources': [
            {'name': name, 'count': info['count']}
            for name, info in sorted_sources
        ],
    }


def discover_and_save(url: str) -> dict:
    """
    抓取异动消息，解析，提取数据源，保存到数据库。

    Returns:
        {total_anomalies, saved, discovered_sources}
    """
    init_log()
    log(f"开始抓取: {url}")

    result = discover_sources(url)
    if 'error' in result:
        return result

    # 保存所有异动消息到数据库（source_name 留空，后续 Step 2 从正文中提取）
    now = now_iso()
    anomalies_to_save = [
        {'title': a['title'], 'url': a['url'], 'publish_time': a['time'] or now, 'source_name': ''}
        for a in result['anomalies']
    ]

    saved = 0
    if anomalies_to_save:
        saved = batch_save_anomaly_news(anomalies_to_save)
        log(f"已保存 {saved} 条到数据库")

    result['saved'] = saved
    return result


# ============================================================================
# 正文抓取（Step 2）
# ============================================================================

async def _crawl_one_content(row: tuple, crawler) -> tuple[int, str]:
    """抓取单篇正文，返回 (news_id, content)"""
    news_id, title, url, publish_time, source_name = row
    if not url:
        return news_id, ""

    try:
        _, html, _ = await _fetch_article_html(url, crawler=crawler)
        if not html:
            return news_id, ""
        content = _extract_content(html, base_url=url)

        # 从正文中提取数据源名称
        extracted_name = extract_source_name(content)
        if extracted_name and extracted_name != '未知':
            source_name_to_save = extracted_name
        else:
            source_name_to_save = ""

        update_anomaly_content(news_id, content, source_name_to_save)
        return news_id, content
    except Exception as e:
        log(f"  [FAIL] {url}: {e}")
        return news_id, ""


async def _fetch_article_html(url: str, crawler=None):
    """抓取文章页 HTML（复用 url-preview 的提取逻辑）"""
    from script.discovery.util.html_fetch import fetch_article_html as _fetch
    return await _fetch(url, return_markdown=True, crawler=crawler)


def _extract_content(html: str, base_url: str = "") -> str:
    """提取正文（复用 url-preview 的 clean_article_html + BeautifulSoup 路径）"""
    from script.discovery.html_cleaner import clean_article_html
    cleaned_html = clean_article_html(html)
    content = _extract_text_from_cleaned(cleaned_html)
    content = _strip_trailing_disclaimer(content)
    return content


# ============================================================================
# 复用 news.py 的 _extract_text_from_cleaned 和 _strip_trailing_disclaimer
# ============================================================================
_CHINESE_RE = re.compile(r'[一-鿿]')
_META_KW_RE = re.compile(r'(来源|发布时间|浏览次数|作者|编辑|出处|稿件来源)\s*[:：]')


def _extract_text_from_cleaned(cleaned_html: str) -> str:
    """从 clean_article_html 输出中提取纯文本正文（与 news.py 的 _extract_text_from_cleaned 完全一致）"""
    from bs4 import BeautifulSoup
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


# 免责声明和风险提示行模式（从末尾向前逐行匹配，命中即剔除）
_DISCLAIMER_RE = re.compile(
    r'^(\(|（)?(投资有风险|股市有风险|入市需谨慎|风险提示|免责条款|免责声明|'
    r'Disclaimer|本文仅供参考|不构成投资建议|据此操作风险自担|'
    r'市场有风险投资需谨慎|证券投资咨询服务提供).*',
    re.IGNORECASE,
)


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


async def _crawl_source_bucket(source_name: str, rows: list, crawler, sem: asyncio.Semaphore, stats: dict, stats_lock: asyncio.Lock):
    """串行抓取单个数据源的正文（同源不并发）"""
    async with sem:
        log(f"  [Bucket] {source_name}: {len(rows)} 篇")
        for row in rows:
            news_id, title, url, _, _ = row
            log(f"    -> {title[:40]}...")
            _, content = await _crawl_one_content(row, crawler)
            async with stats_lock:
                if content and len(content) >= 50:
                    update_anomaly_content(news_id, content)
                    log(f"      [OK] {len(content)} 字")
                    stats["ok"] += 1
                else:
                    log(f"      [SKIP] 正文过短或为空")
                    stats["fail"] += 1


async def _crawl_contents_batch(limit: int = 200) -> dict:
    """批量抓取异动消息正文（跨源并发，源内串行）"""
    rows = get_anomaly_news_for_content_crawl(limit=limit)
    if not rows:
        log("无待采集正文的记录")
        return {"total": 0, "ok": 0, "fail": 0}

    # 按 source_name 分桶
    buckets: dict[str, list] = {}
    for row in rows:
        buckets.setdefault(row[4], []).append(row)
    log(f"待采集正文: {len(rows)} 篇，{len(buckets)} 个数据源")

    from crawl4ai import AsyncWebCrawler, BrowserConfig
    sem = asyncio.Semaphore(3)  # 跨源并发上限
    stats: dict[str, int] = {"ok": 0, "fail": 0}
    stats_lock = asyncio.Lock()

    async with AsyncWebCrawler(config=BrowserConfig(headless=True)) as crawler:
        await asyncio.gather(*[
            _crawl_source_bucket(src, src_rows, crawler, sem, stats, stats_lock)
            for src, src_rows in buckets.items()
        ])

    return stats


def crawl_anomaly_contents(limit: int = 200) -> dict:
    """正文抓取入口（供 pipeline Step 2 调用）"""
    init_log()
    log("=" * 60)
    log("Step 2: 采集异动消息正文")
    log("=" * 60)

    stats = asyncio.run(_crawl_contents_batch(limit=limit))
    log(f"正文采集完成: ok={stats['ok']}, fail={stats['fail']}")
    return stats
