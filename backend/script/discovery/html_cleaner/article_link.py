"""
article_link.py - 文章链接提取
"""

from __future__ import annotations

import re

from ._constants import (
    MARKDOWN_LINK_RE,
    WHITESPACE_RE,
    BRACKET_TRAILING_RE,
    PLAIN_URL_RE,
    BROKEN_LINK_RE,
    IMG_URL_RE,
    FILE_EXT_RE,
    _HTTP_PREFIX_RE,
    _HEADER_START_RE,
    _EXT_TRAILING_RE,
    _TITLE_PREFIX_RE,
    _ARTICLE_URL_RE,
    _MARKDOWN_TITLE_URL_RE,
)
from .title import clean_title


def extract_links_from_html(html: str, source_name: str) -> list[dict]:
    """
    直接从原始 HTML 提取文章链接和标题（兜底方案）。
    """
    articles = []
    seen = set()

    for um in _ARTICLE_URL_RE.finditer(html):
        url = um.group().strip()
        from script.crawl.article_regex import is_article_url
        if not is_article_url(url) or url in seen:
            continue
        seen.add(url)
        pos = um.start()
        op = html.rfind('<a ', 0, pos)
        if op < 0:
            op = html.rfind('<a>', 0, pos)
        if op < 0:
            continue
        chunk = html[max(0, op - 600):min(len(html), um.end() + 100)]
        visible = re.sub(r'<[^>]+>', ' ', chunk)
        visible = re.sub(r'\s+', ' ', visible).strip()
        url_short = url.split('?')[0]
        basename = url_short.split('/')[-1]
        url_pos = visible.lower().rfind(basename.lower())
        if url_pos < 0:
            url_pos = visible.lower().rfind(url_short.lower())
        before = visible[:url_pos] if url_pos >= 0 else visible
        cn_chunks = re.findall(r'[一-鿿]{5,40}', before)
        title = cn_chunks[-1] if cn_chunks else url
        from script.common.util import parse_publish_time
        date_str = parse_publish_time(title)
        if date_str:
            title = re.sub(r'\s*\d{4}[-/.]\d{1,2}[-/.]\d{1,2}\s*$', '', title).rstrip()
        articles.append({
            "source_name": source_name,
            "title": title,
            "url": url,
            "publish_time": date_str or ""
        })
    return articles


def extract_article_links(
    markdown: str, source_name: str, html: str = "", headline: str = ""
) -> list[dict]:
    """
    从列表页 markdown（或原始 HTML）中提取文章链接和标题。

    策略（按优先级）：
    1. Markdown [标题](URL) 格式
    2. 损坏的 Markdown 链接：标题](URL)
    3. 纯文本 URL（crawl4ai 转换失败的兜底）
    4. 原始 HTML 提取（当以上均无结果时）
    """
    from script.crawl.date_utils import extract_date_from_context
    from script.crawl.article_regex import is_article_url

    articles = []
    seen = set()
    lines = markdown.split("\n")

    for i, line in enumerate(lines):
        ls = line.strip()
        if not ls:
            continue

        # 模式1: 标准 Markdown [标题](URL)
        m1 = _MARKDOWN_TITLE_URL_RE.search(ls)
        if m1:
            title = m1.group(1).strip()
            url = m1.group(2).strip()
            if len(title) >= 5 and len(url) >= 10 and is_article_url(url) and url not in seen:
                seen.add(url)
                date_str = extract_date_from_context(title, ls, m1.end(), lines, i)
                articles.append({"source_name": source_name, "title": clean_title(title), "url": url, "publish_time": date_str or ""})
                continue

        # 模式2: 损坏的 Markdown 链接 标题](URL)
        for m2 in BROKEN_LINK_RE.finditer(ls):
            title = m2.group(1).strip()
            url = m2.group(2).strip()
            if IMG_URL_RE.search(url) or not _HTTP_PREFIX_RE.match(url):
                continue
            if FILE_EXT_RE.search(title) or _HEADER_START_RE.match(title) or _EXT_TRAILING_RE.match(title):
                continue
            if len(title) < 3 or len(url) < 10 or not is_article_url(url) or url in seen:
                continue
            seen.add(url)
            date_str = extract_date_from_context(title, ls, m2.end(), lines, i)
            articles.append({"source_name": source_name, "title": clean_title(title), "url": url, "publish_time": date_str or ""})
            break

        # 模式3: 纯文本 URL
        for um in PLAIN_URL_RE.finditer(ls):
            url = um.group().strip()
            if ']' in url or '#' in url or not (url.startswith('http://') or url.startswith('https://')):
                continue
            if not is_article_url(url) or url in seen:
                continue
            seen.add(url)

            before_full = ls[:um.start()]
            search_window = before_full[-500:]
            line_for_search = MARKDOWN_LINK_RE.sub('', search_window)
            close_bracket = line_for_search.rfind('](')
            if close_bracket < 0:
                cand = search_window.strip()
            else:
                open_bracket = line_for_search.rfind('[', 0, close_bracket)
                cand = line_for_search[open_bracket + 1:close_bracket].strip() if open_bracket >= 0 else line_for_search[:close_bracket].strip()

            cand = MARKDOWN_LINK_RE.sub('', cand)
            cand = WHITESPACE_RE.sub(' ', cand).strip()
            cand = BRACKET_TRAILING_RE.sub('', cand).strip()

            if (len(cand) < 5 or not cand) and i > 0:
                prev = lines[i - 1].strip()
                if prev and not prev.startswith('http') and len(prev) >= 5:
                    cand = _TITLE_PREFIX_RE.sub('', prev).strip()
                    cand = MARKDOWN_LINK_RE.sub('', cand)
                    cand = WHITESPACE_RE.sub(' ', cand).strip()

            title = cand if cand and len(cand) >= 5 else url
            title = clean_title(title)
            date_str = extract_date_from_context(title, ls, um.end(), lines, i)
            articles.append({"source_name": source_name, "title": title, "url": url, "publish_time": date_str or ""})

    # 4. 兜底：原始 HTML 提取
    if not articles and html:
        articles = extract_links_from_html(html, source_name)

    return articles