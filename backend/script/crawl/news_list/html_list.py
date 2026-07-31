"""
html_list.py - HTML类型数据源采集

使用 fetch_rendered_html 抓取列表页，提取文章标题、发布日期、摘要。
"""
import asyncio
import json
import re
import logging
from datetime import datetime
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from script.log import log as _log
from script.common.jsonutil import parse_json_field
from script.discovery.html_cleaner import clean_boilerplate_text, clean_markdown_text
from script.common.util import parse_publish_time, is_today
from script.crawl.crawl_db import insert_article, upsert_list_page
from script.discovery.util.html_fetch import fetch_list_html

# 静默 Crawl4AI 初始化日志（→ Crawl4AI x.x.x）
for _logger_name in ["crawl4ai", "Crawl4AI"]:
    _l = logging.getLogger(_logger_name)
    _l.setLevel(logging.WARNING)

# 常量
MAX_SUBTITLE_LEN = 300
MAX_ARTICLES_PER_SOURCE = 500  # 每源硬上限，防止意外循环


# 纯时间格式（HH:MM / HH:MM:SS）→ 今天日期 + 该时间
_TIMEOnly_RE = re.compile(r'^\s*(\d{1,2}):(\d{2})(?::(\d{2}))?\s*$')


def _parse_time_only_as_today(text: str) -> str | None:
    """
    处理"纯时间"格式（直播流常见，只显示 HH:MM:SS）。
    parse_publish_time 不支持，返回 None；这里兜底为今天 + 该时间。
    """
    if not text:
        return None
    m = _TIMEOnly_RE.match(text)
    if not m:
        return None
    today = datetime.now().strftime('%Y-%m-%d')
    h, mi, sec = m.group(1), m.group(2), m.group(3) or '00'
    try:
        return f"{today} {int(h):02d}:{int(mi):02d}:{int(sec):02d}"
    except ValueError:
        return None


def log(msg: str):
    _log("list_crawler", msg)


def _extract_attr_by_selector(element: BeautifulSoup, selector: str, attr: str) -> str:
    """
    从 element 中提取属性值。

    支持两种 selector 格式：
    1. CSS selector: "ul.news-list li a"
    2. tag@attr 格式: "a@href" (从 element 直接获取 href)
    3. CSS@attr 格式: "ul.news-list li a@href" (先选元素，再取属性)

    Args:
        element: BeautifulSoup 元素
        selector: 选择器字符串
        attr: 要提取的属性名

    Returns:
        属性值字符串
    """
    if not selector or not attr:
        return ""

    if '@' in selector:
        # tag@attr 格式
        parts = selector.split('@', 1)
        css_sel = parts[0].strip()
        attr_name = parts[1].strip() if len(parts) > 1 else attr
        if not css_sel:
            # 直接是 @attr 格式，从 element 获取
            return element.get(attr_name, "")
        try:
            el = element.select_one(css_sel)
            if el:
                return el.get(attr_name, "")
        except Exception:
            pass
    else:
        # 纯 CSS selector，从中选择元素获取属性
        try:
            el = element.select_one(selector)
            if el:
                return el.get(attr, "")
        except Exception:
            pass

    return ""


def is_article_url(url: str) -> bool:
    """排除列表页、分类页等非文章 URL"""
    if url.lower().endswith('.gif'):
        return False
    if '?s=' in url or '/category/' in url or '/topic/' in url or '/channel/' in url:
        return False
    if any(k in url.lower() for k in ['/node/', '/list/', '/index']):
        return False
    news_match = re.search(r'/news(/|$|\?)', url)
    if news_match:
        # 支持两种日期格式：/news/2026/06/09/ 和 /news/20260609/
        has_date_slug = bool(re.search(r'/news/\d{4}/\d{2}/\d{2}/', url))
        has_date_compact = bool(re.search(r'/news/\d{8}/', url))
        has_article_path = bool(re.search(r'/news/\d{4}/\d{2}/\d{2}/[^/]+', url))
        has_article_compact = bool(re.search(r'/news/\d{8}/[^/]+\.shtml', url))
        if not has_date_slug and not has_date_compact and not has_article_path and not has_article_compact:
            return False
        return True
    # 处理 news.10jqka.com.cn 这种域名中包含 news 的情况
    #路径格式：/YYYYMMDD/article_id.shtml
    if re.search(r'news\..+\.com\.cn/\d{8}/', url):
        return True
    if any(p in url.lower() for p in ['/article/', '/info/', '/detail/', '/show/']):
        return True
    return False


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

        nav_titles = {
            'view more', 'first page', 'previous page', 'next page', 'last page',
            'read more', 'view all', 'home', 'sign in', 'logout', 'member center',
            'trendforce', 'news logo', 'news',
        }
        is_nav = title.lower() in nav_titles or title.lower().startswith('![')

        article_title = title
        summary_candidate = None

        if is_nav:
            for look in range(1, 8):
                if i + look >= len(lines):
                    break
                cand = lines[i + look].strip()
                if cand.startswith('![') or cand.startswith('[ ') or not cand:
                    continue
                m2 = re.search(r'\*\*(.+?)\*\*', cand)
                if m2:
                    candidate = m2.group(1).strip()
                    candidate = re.sub(r'^\s*\[News\]\s*', '', candidate, flags=re.IGNORECASE)
                    if len(candidate) > 5:
                        article_title = candidate
                        summary_candidate = cand
                        break
                elif cand.startswith('## ') or cand.startswith('# '):
                    candidate = re.sub(r'^#+\s*', '', cand)
                    candidate = re.sub(r'^\*\*(.+?)\*\*$', r'\1', candidate).strip()
                    candidate = re.sub(r'^\s*\[News\]\s*', '', candidate, flags=re.IGNORECASE)
                    if len(candidate) > 5:
                        article_title = candidate
                        summary_candidate = cand
                        break

        date_str = None
        slug_match = re.search(r'/(\d{4}/\d{2}/\d{2})/', url)
        if slug_match:
            date_str = slug_match.group(1).replace('/', '-')

        if not date_str:
            found = parse_publish_time(article_title)
            if found:
                date_str = found
                article_title = re.sub(r'\s*\d{4}[-/.]\d{1,2}[-/.]\d{1,2}\s*$', '', article_title).rstrip()

        if not date_str and summary_candidate:
            found = parse_publish_time(summary_candidate)
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

        summary = ""
        if is_nav and summary_candidate:
            for j in range(i + look + 1, i + look + 8):
                if j >= len(lines):
                    break
                nxt = lines[j].strip()
                if not nxt or nxt.startswith('![') or nxt.startswith('[') or nxt.startswith('#'):
                    continue
                nxt = clean_markdown_text(nxt)
                if nxt and len(nxt) > 10:
                    summary = nxt[:MAX_SUBTITLE_LEN]
                    break

        if is_nav and not summary_candidate:
            i += 1
            continue

        article_title = article_title.strip().strip('[').strip(']').strip()
        articles.append({
            "source_name": source_name,
            "title": article_title,
            "url": url,
            "summary": summary,
            "list_date": date_str,
        })
        i += 1
    return articles


def _find_element_by_text_content(element, tag_name, class_contains):
    """通过标签名和类名中包含的关键字查找元素（处理 Tailwind CSS 括号语法）"""
    for elem in element.find_all(tag_name):
        classes = elem.get('class', [])
        if any(class_contains in c for c in classes):
            return elem
    return None


def _is_element_before(el1, el2) -> bool:
    """判断 el1 是否在 el2 之前（DOM 树中更靠前）"""
    # 使用 BeautifulSoup 的 next/previous element 遍历来比较位置
    # 顺着 el2 的 previous 遍历，如果遇到 el1 则 el1 在 el2 之前
    for el in el2.previous_elements:
        if el is el1:
            return True
    return False


def _extract_tailwind_keyword(selector: str) -> str:
    """从 Tailwind CSS 选择器中提取类名字干，如 'h3.text-[15px]' -> 'text-'"""
    match = re.search(r'(text-\[?[^\s\]]+\]?)', selector)
    if match:
        return match.group(1).split('.')[0]
    return ""


def _build_selector_from_reverse(list_config: dict) -> dict:
    """
    从逆推配置构建 CSS 选择器配置。

    逆推配置格式:
        {
            "type": "reverse",
            "container_tag": "div",
            "container_class": "flex flex-col gap-5",
            "item_tag": "a",
            "item_selector": "div a[href]",
            "css_selector": "div a[href]",
        }

    返回 extract_with_css_selectors 期望的 selector 配置格式:
        {
            "item": "div a[href]",
            "title": "a",
            "url": "a[href]",
        }
    """
    css_selector = list_config.get("css_selector") or list_config.get("item_selector")
    if not css_selector:
        container_tag = list_config.get("container_tag", "div")
        item_tag = list_config.get("item_tag", "a")
        css_selector = f"{container_tag} {item_tag}[href]"

    # 清理 LLM 返回的选择器（去除不必要的转义）
    def clean_selector(sel):
        if not sel:
            return sel
        # 去除 CSS 选择器中 LLM 可能添加的转义
        return sel.replace(r'\-', '-').replace(r'\[', '[').replace(r'\]', ']')

    field_selectors = {}
    raw_fs = list_config.get("field_selectors", {})
    for k, v in raw_fs.items():
        field_selectors[k] = clean_selector(v) if isinstance(v, str) else v

    return {
        "item": css_selector,
        "title": list_config.get("item_tag", "a"),
        "url": f"{list_config.get('item_tag', 'a')}[href]",
        # 保留 LLM 分析出的字段选择器（已清理）
        "field_selectors": field_selectors,
    }


def extract_with_css_selectors(html: str, source_name: str, list_config: dict, base_url: str = "") -> list[dict]:
    """使用 list_config 中的 CSS 选择器从列表页 HTML提取文章"""
    selector_cfg = list_config.get("selector", {})
    if not selector_cfg:
        return []

    # 构建 item 选择器：优先用 css_selector（完整路径），否则结合 container + item
    container_sel = selector_cfg.get("container", "")
    item_only_sel = selector_cfg.get("item", "li")
    css_selector = selector_cfg.get("css_selector", "")

    # 决定 item_sel：css_selector 存在且不等于 container 时才使用，否则用 container+item
    if css_selector and css_selector.strip() and css_selector != container_sel:
        # css_selector 是完整路径（不等于 container），使用它
        item_sel = css_selector
    elif container_sel and item_only_sel:
        # 如果 item 已包含 container 路径（冗余设计），直接用 item
        if item_only_sel.startswith(container_sel):
            item_sel = item_only_sel
        else:
            item_sel = f"{container_sel} {item_only_sel}"
    elif item_only_sel:
        item_sel = item_only_sel
    else:
        item_sel = "li"
    #优先使用 LLM 分析出的精确选择器
    field_selectors = selector_cfg.get("field_selectors", {})
    title_sel = field_selectors.get("title_selector") or selector_cfg.get("title", "a")
    url_sel = field_selectors.get("url_selector") or selector_cfg.get("url", "a")
    date_sel = field_selectors.get("time_selector") or selector_cfg.get("date", "")
    summary_sel = field_selectors.get("summary_selector") or selector_cfg.get("summary", "")
    content_sel = selector_cfg.get("content", "")
    title_date_pat = selector_cfg.get("titleDateRemovePattern", "")
    title_product_only = selector_cfg.get("titleProductOnly", False)

    soup = BeautifulSoup(html, 'html.parser')
    articles = []

    try:
        items = soup.select(item_sel)
    except Exception:
        return []

    for item in items:
        date_str = None
        if date_sel:
            try:
                date_el = item.select_one(date_sel)
                if date_el:
                    date_str = date_el.get_text(strip=True)
                    raw_date_text = date_str
                    date_str = parse_publish_time(date_str)
                    # 纯时间格式（HH:MM / HH:MM:SS）回退：视为今天
                    if not date_str and raw_date_text:
                        date_str = _parse_time_only_as_today(raw_date_text)
            except Exception:
                pass

        title_el = None
        try:
            title_el = item.select_one(title_sel)
        except Exception:
            pass

        # 如果 CSS 选择器失败，尝试通过类名关键字查找
        if not title_el and title_sel.startswith('h') and 'text-' in title_sel:
            keyword = _extract_tailwind_keyword(title_sel)
            if keyword:
                title_el = _find_element_by_text_content(item, 'h3', keyword)

        # 如果 title_sel 为 "a" 且 item 是 <a> 标签，先查找内部 heading 元素
        # 避免提取到日期+作者+标题+摘要等全部文本
        if not title_el and item.name == 'a' and title_sel == 'a':
            heading_el = item.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
            if heading_el:
                title_el = heading_el

        # 如果 title_el 选中了 item 自身（即选择器返回了容器本身），且 item 内有 heading 子元素，
        # 说明选择器太宽泛，语义上的标题是内部的 h1-h6，优先使用 heading（通用回退，适用于所有卡片式列表）
        if title_el is item and item.name in ('a', 'div', 'section', 'article', 'li'):
            heading_el = item.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
            if heading_el:
                title_el = heading_el

        # 如果仍然没找到title元素，且item本身是链接，使用item本身
        if not title_el and item.name == 'a':
            title_el = item

        # 如果还是没找到，但 field_selectors 被使用过，尝试直接获取链接文本
        if not title_el:
            # 最后 fallback：直接用 item 的文本（适用于纯文本节点）
            title_text = item.get_text(separator='', strip=True)
            if len(title_text) > 2:
                title_el = item  # 使用 item 作为占位

        if not title_el:
            continue

        # URL 提取：优先用 url_sel（支持 CSS selector 或 tag@attr 格式）
        url = ""
        if url_sel:
            url = _extract_attr_by_selector(item, url_sel, "href")
        if not url:
            # Fallback: 从 title_el 或 item 获取
            url = title_el.get("href", "") if hasattr(title_el, 'get') else ""
            if not url and item.name == 'a':
                url = item.get("href", "")
        # 相对路径拼接 base_url
        if url and base_url and not url.startswith(('http://', 'https://', '//')):
            url = urljoin(base_url, url)

        # 从 URL 提取日期（支持四种格式）
        if not date_str and url:
            # 格式1: /2026/06/11/
            slug_match = re.search(r'/(\d{4}/\d{2}/\d{2})/', url)
            if slug_match:
                date_str = slug_match.group(1).replace('/', '-')
            else:
                # 格式2: /2026-06-11/ (dash 分隔)
                dash_match = re.search(r'/(\d{4}-\d{2}-\d{2})/', url)
                if dash_match:
                    date_str = dash_match.group(1)
                else:
                    # 格式3: /20260611/ (紧凑格式)
                    compact_match = re.search(r'/(\d{8})/', url)
                    if compact_match:
                        date_str = f"{compact_match.group(1)[:4]}-{compact_match.group(1)[4:6]}-{compact_match.group(1)[6:8]}"
                    else:
                        # 格式4: /2026/0618/ (人民网/年/MMDD 格式)
                        year_mmdd_match = re.search(r'/(\d{4})/(\d{4})/', url)
                        if year_mmdd_match:
                            y, mmdd = year_mmdd_match.group(1), year_mmdd_match.group(2)
                            date_str = f"{y}-{mmdd[:2]}-{mmdd[2:]}"

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

        summary = ""
        #优先用 LLM 分析出的 summary_selector
        if summary_sel:
            try:
                summary_el = item.select_one(summary_sel)
                if summary_el:
                    # 如果匹配的元素在 title 之前，可能是误匹配（日期/作者段落）
                    # 尝试找后续的同类元素
                    if title_el and summary_sel.startswith('p') and _is_element_before(summary_el, title_el):
                        all_els = item.select(summary_sel)
                        for el in all_els:
                            if not _is_element_before(el, title_el):
                                summary_el = el
                                break
                    summary = summary_el.get_text(separator=' ', strip=True)[:MAX_SUBTITLE_LEN]
            except Exception:
                # Fallback: 通过类名关键字查找
                if 'text-' in summary_sel:
                    keyword = _extract_tailwind_keyword(summary_sel)
                    if keyword:
                        summary_el = _find_element_by_text_content(item, 'p', keyword)
                        if summary_el:
                            summary = summary_el.get_text(separator=' ', strip=True)[:MAX_SUBTITLE_LEN]
        elif content_sel:
            try:
                content_el = item.select_one(content_sel)
                if content_el:
                    content = content_el.get_text(separator=' ', strip=True)
                    content = clean_boilerplate_text(content)
                    summary = content[:MAX_SUBTITLE_LEN] if content else ""
            except Exception:
                pass

        articles.append({
            "source_name": source_name,
            "title": title_text,
            "url": url,
            "time": date_str or "",
            "summary": summary,
        })

    return articles


def extract_list_articles(html: str, markdown: str, source_name: str, list_config: dict | None, base_url: str = "") -> list[dict]:
    """提取列表页文章，不入库。返回 [{"title": "", "url": "", "time": "", "summary": ""}, ...]"""
    if not html and not markdown:
        return []

    list_config = list_config or {}
    config_type = list_config.get("type", "")

    # CSS 选择器提取（优先使用）
    css_articles = []
    use_css_selector = False
    if config_type == "html" and list_config.get("selector"):
        css_articles = extract_with_css_selectors(html, source_name, list_config, base_url)
        if css_articles:
            use_css_selector = True

    # 先用 markdown 提取（不过滤 is_article_url）
    phase1_articles = _extract_article_links_from_markdown(markdown or "", source_name) if markdown else []

    if use_css_selector:
        # 检查 CSS 选择器结果是否有有效的 URL
        css_urls_valid = any(a.get("url") for a in css_articles)
        if css_urls_valid:
            # CSS 选择器有有效 URL，直接返回
            return css_articles
        # CSS 选择器 URL 全为空，尝试从 markdown 补充
        for art in css_articles:
            if not art.get("url"):
                title = art.get("title", "")
                for m_art in phase1_articles:
                    if m_art.get("title") == title and m_art.get("url"):
                        art["url"] = m_art["url"]
                        break
        # 再次检查是否有 URL
        if any(a.get("url") for a in css_articles):
            return css_articles
        # CSS 选择器仍然没有有效 URL，但有有效内容（时间+标题），直接返回
        if css_articles and any((a.get("time") or a.get("title")) for a in css_articles):
            return css_articles
        # CSS 选择器没有有效内容，回退到 HTML 直接提取
        return _extract_links_from_html_fallback(html, source_name, base_url)
    elif phase1_articles:
        # 没有 CSS 选择器时，用 markdown 结果
        return phase1_articles
    else:
        # markdown 提取失败，回退到直接解析 HTML
        return _extract_links_from_html_fallback(html, source_name, base_url)


def _extract_article_links_from_markdown(markdown: str, source_name: str) -> list[dict]:
    """从 markdown 提取文章链接，不过滤 is_article_url（用于 API 显示）"""
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

        nav_titles = {
            'view more', 'first page', 'previous page', 'next page', 'last page',
            'read more', 'view all', 'home', 'sign in', 'logout', 'member center',
            'trendforce', 'news logo', 'news',
        }
        is_nav = title.lower() in nav_titles or title.lower().startswith('![')

        article_title = title
        summary_candidate = None

        if is_nav:
            for look in range(1, 8):
                if i + look >= len(lines):
                    break
                cand = lines[i + look].strip()
                if cand.startswith('![') or cand.startswith('[ ') or not cand:
                    continue
                m2 = re.search(r'\*\*(.+?)\*\*', cand)
                if m2:
                    candidate = m2.group(1).strip()
                    candidate = re.sub(r'^\s*\[News\]\s*', '', candidate, flags=re.IGNORECASE)
                    if len(candidate) > 5:
                        article_title = candidate
                        summary_candidate = cand
                        break
                elif cand.startswith('## ') or cand.startswith('# '):
                    candidate = re.sub(r'^#+\s*', '', cand)
                    if len(candidate) > 5:
                        article_title = candidate
                        summary_candidate = cand
                        break

        articles.append({
            "source_name": source_name,
            "title": article_title,
            "url": url,
            "summary": summary_candidate or "",
        })
        i += 1
    return articles


def _extract_links_from_html_fallback(html: str, source_name: str, base_url: str = "") -> list[dict]:
    """从 HTML 直接提取链接（不过滤任何 URL 模式）"""
    from bs4 import BeautifulSoup
    from urllib.parse import urljoin

    articles = []
    soup = BeautifulSoup(html, 'html.parser')

    # 查找所有文章链接（包含日期 slug 的 URL）
    for a in soup.find_all('a', href=True):
        href = a.get('href', '')
        title = a.get_text(strip=True)

        # 跳过导航链接
        if len(title) <= 5:
            continue
        if any(k in href.lower() for k in ['/index', '/list', '/node', '/category', '/topic', '/channel']):
            continue
        if href.endswith('.gif') or '?s=' in href:
            continue

        # 跳过没有日期格式的链接
        date_pattern = re.search(r'/(\d{4}-\d{2}-\d{2})/', href)
        if not date_pattern:
            continue

        # 补全相对 URL
        if href.startswith('//'):
            url = 'https:' + href
        elif href.startswith('/'):
            if base_url:
                from urllib.parse import urlparse
                base = urlparse(base_url)
                url = f'{base.scheme}://{base.netloc}{href}'
            else:
                url = href
        else:
            url = href

        articles.append({
            "source_name": source_name,
            "title": title,
            "url": url,
            "time": date_pattern.group(1) if date_pattern else "",
            "summary": "",
        })
    return articles[:50]  # 限制数量


async def crawl_html_source(
    source: dict,
    batch_id: int,
    global_limit: int,
    global_max_consecutive: int,
    existing_urls: set,
    target_date=None,
    crawler: "AsyncWebCrawler | None" = None,
) -> dict:
    """采集单个 HTML 类型数据源，返回统计 dict。

    Args:
        crawler: 可选的已开浏览器实例（复用单个 Chromium 进程，避免每源启停浏览器）。
                 不传则按旧行为每源临时开一个，向后兼容。
    """
    name = source["name"]
    list_url = source.get("url_norm") or source.get("url", "")
    craw_limit = source.get("crawNumPerSource", global_limit)
    list_config_str = source.get("list_config")
    list_config = parse_json_field(list_config_str) if list_config_str else None
    # 新配置规则：list_complete=True 表示列表页已含完整信息，
    # 入库时把 summary 写入 content，下游 article_crawler 会自动跳过抓取
    list_complete = bool(list_config.get("list_complete", False)) if isinstance(list_config, dict) else False

    log(f"\n-> Phase1 [List] {name}: {list_url}")

    # 统一走 fetch_list_html 入口（自动等待 JS 渲染；crawler 可选复用，生产批量时 list_crawler.py 传入）
    try:
        _, html, markdown = await fetch_list_html(
            list_url,
            return_markdown=True,
            crawler=crawler,
        )
    except Exception as e:
        log(f"  [FAIL] list page exception: {e}")
        return None

    if not html:
        log(f"  [FAIL] list page: empty html")
        return None

    # 与 /api/news/fetch 完全相同的提取入口（CSS → markdown 补 URL → HTML fallback 三级兜底）
    articles = extract_list_articles(html or "", markdown or "", name, list_config or {}, list_url)
    log(f"  [P1] 提取到 {len(articles)} 个文章链接")

    # 是否走 CSS 选择器模式（用于决定后续入库路径：upsert_list_page vs insert_article）
    use_css_selector = bool(
        list_config
        and list_config.get("type") == "html"
        and list_config.get("selector")
    )

    # CLI 专有：去重（已有 URL 不入库）
    new_articles = [a for a in articles if not a.get("url") or a["url"] not in existing_urls]
    log(f"  [P1] 其中 {len(new_articles)} 条未入库")

    if not new_articles:
        return None

    max_consec = global_max_consecutive
    consecutive_not_today = 0
    local_today = local_old = local_no_date = local_processed = 0
    no_date_sources = {}

    for art in new_articles:
        if local_processed >= MAX_ARTICLES_PER_SOURCE:
            log(f"  [P1] 已达硬上限 {MAX_ARTICLES_PER_SOURCE}，停止该源")
            break
        if craw_limit and craw_limit > 0 and local_processed >= craw_limit:
            log(f"  [P1] 已达每源采集上限 {craw_limit}，停止该源")
            break
        local_processed += 1

        # 标题少于10个字不存储，但日志正常输出
        if len(art.get("title", "")) < 10:
            log(f"  -> {art['title'][:40]}... [SKIP] 标题过短（{len(art.get('title', ''))}字）")
            continue

        if consecutive_not_today >= max_consec:
            log(f"  [P1] 连续 {consecutive_not_today} 篇非当天，已达上限 {max_consec}，停止该源")
            break

        pub_time = art.get("time") or art.get("list_date") or art.get("publish_time") or ""

        if not pub_time:
            if use_css_selector and not art.get("url"):
                local_no_date += 1
                if name not in no_date_sources:
                    no_date_sources[name] = 0
                no_date_sources[name] += 1
                log(f"  -> {art['title'][:40]}... [SKIP] CSS选择器模式无日期")
                continue
            insert_article({
                "source_name": name,
                "title": art["title"],
                "url": art["url"],
                "summary": art.get("summary", ""),
                "publish_time": "",
                "content": art.get("content", ""),
                "content_length": len(art.get("content", "") or ""),
                "batch_id": batch_id,
            }, batch_id)
            log(f"  -> {art['title'][:40]}... [NO-DATE] 已入库，news_filter 判断")
            continue

        if not is_today(pub_time):
            local_old += 1
            consecutive_not_today += 1
            log(f"  -> {art['title'][:40]}... [SKIP] 非当天 {pub_time}（连续 {consecutive_not_today}/{max_consec}）")
            continue

        consecutive_not_today = 0

        if use_css_selector:
            # 新配置规则：list_complete=True 时把 summary 写入 content
            article_content = art.get("content", "")
            if list_complete and not article_content:
                article_content = art.get("summary", "")
                if article_content:
                    log(f"  -> {art['title'][:40]}... [LIST_COMPLETE] summary→content ({len(article_content)}字)")
            ok = upsert_list_page({
                "source_name": name,
                "title": art["title"],
                "url": art["url"],
                "summary": art.get("summary", ""),
                "publish_time": pub_time,
                "content": article_content,
            }, batch_id)
            if ok:
                local_today += 1
                if art["url"]:
                    existing_urls.add(art["url"])
        else:
            content = art.get("content", "") or art.get("summary", "")
            ok = insert_article({
                "source_name": name,
                "title": art["title"],
                "url": art["url"],
                "summary": art.get("summary", ""),
                "publish_time": pub_time,
                "content": content,
                "content_length": len(content),
                "batch_id": batch_id,
            }, batch_id)
            if ok:
                local_today += 1
                existing_urls.add(art["url"])

        log(f"  -> {art['title'][:40]}... [OK] {pub_time}")
        await asyncio.sleep(0.3)

    log(f"  [P1] {name} 结果: 当天入库 {local_today}, 非当天 {local_old}, 无法确认日期 {local_no_date}, 已采 {local_processed}/{craw_limit or '无上限'}")
    return {
        "today": local_today, "old": local_old, "no_date": local_no_date,
        "processed": local_processed, "no_date_sources": no_date_sources,
    }