"""
content.py - 正文内容提取（正则兜底）
"""

from __future__ import annotations

import re
import html as html_module

from ._constants import (
    CONTENT_EXTRACT_PATTERNS,
    HTML_EXTRACT_PATTERNS,
)
from .boilerplate import clean_boilerplate_text, _is_boilerplate_para

# =============================================================================
# 正则兜底提取
# =============================================================================

def _detect_source(url: str = "", html: str = "") -> str:
    """检测文章来源"""
    if html:
        if "cnenergynews.cn" in html or 'class="article_content"' in html or 'class="w-createtime"' in html:
            return "cnenergynews"
        if 'id="news_detail"' in html or 'class="news_detail"' in html:
            return "mydrivers"
        if 'class="live_detail"' in html or "news.smm.cn" in html:
            return "smm"
        if 'class="people_news_content"' in html:
            return "people"
        if 'class="article"' in html and 'pubdate' in html:
            return "cnenergynews"
    if url:
        for domain, name in [
            ("mydrivers.com", "mydrivers"),
            ("cnenergynews.cn", "cnenergynews"),
            ("smm.cn", "smm"),
            ("people.com.cn", "people"),
            ("moa.gov.cn", "moa"),
        ]:
            if domain in url:
                return name
    return "unknown"


def _extract_content_fallback(html: str) -> str:
    """正则兜底提取正文"""
    area = ""
    for pat, flags in HTML_EXTRACT_PATTERNS:
        m = re.search(pat, html, flags)
        if m:
            area = m.group(1)
            break

    if area:
        paras = re.findall(r'<p[^>]*>(.*?)</p>', area, re.DOTALL | re.IGNORECASE)
        blocks = []
        for p in paras:
            t = re.sub(r'<[^>]+>', '', p)
            t = html_module.unescape(t).strip()
            if len(t) >= 15 and not _is_boilerplate_para(t):
                blocks.append(t)
        if blocks:
            return ' '.join(blocks)

    paras = re.findall(r'<p[^>]*>(.*?)</p>', html, re.DOTALL | re.IGNORECASE)
    blocks = []
    for p in paras:
        t = re.sub(r'<[^>]+>', '', p)
        t = html_module.unescape(t).strip()
        if len(t) >= 15 and not _is_boilerplate_para(t):
            blocks.append(t)
    if blocks:
        return ' '.join(blocks)

    t = re.sub(r'<[^>]+>', ' ', html)
    t = html_module.unescape(t)
    return re.sub(r'\s{3,}', ' ', t).strip()


def extract_content_from_html(html: str, url: str = "") -> dict:
    """
    从原始 HTML 提取文章正文内容（正则兜底方案）。

    Returns:
        dict: {content, ai_summary, source, raw_length}
    """
    result = {
        "content": "",
        "ai_summary": "",
        "source": _detect_source(url, html),
        "raw_length": len(html),
    }
    if not html or not html.strip():
        return result

    # AI 摘要
    m = re.search(r'AI摘要[^>]*内容由AI生成[^>]*"([^"]{20,})"', html)
    if not m:
        m = re.search(r'"AI摘要"[^>]*>([^<]{50,})', html)
    if m:
        result["ai_summary"] = m.group(1).strip()

    content = ""
    patterns = CONTENT_EXTRACT_PATTERNS
    if result["source"] == "mydrivers":
        patterns = CONTENT_EXTRACT_PATTERNS[1:]

    for pat, flags in patterns:
        m = re.search(pat, html, flags)
        if m:
            cand = m.group(1) if m.lastindex else m.group(0)
            text = re.sub(r'<[^>]+>', '', cand)
            text = html_module.unescape(text)
            text = re.sub(r'\s+', ' ', text).strip()
            if len(text) >= 200:
                content = text
                break

    if not content:
        content = _extract_content_fallback(html)

    if content:
        content = re.sub(r'!\[([^\]]*)\]\([^)]+\)', '', content)
        content = re.sub(r'\[\]\([^)]+\)', '', content)
        content = re.sub(r'#{1,6}\s+', '', content)
        content = re.sub(r'\s+', ' ', content).strip()
        content = content.rstrip('【本文结束】').rstrip()

    result["content"] = content
    return result