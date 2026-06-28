# _extract.py - 从清洗后的 HTML 提取新闻列表（对外 API）

import re

from bs4 import BeautifulSoup

from .._constants import NEWS_URL_REGEX

# URL 中日期路径匹配：/2026-06-13/ 或 /2026/06/13/
_DATE_PATH_RE = re.compile(r"/(\d{4})[-/](\d{2})[-/](\d{2})/")


def extract_news_list_from_cleaned(cleaned_html: str) -> list[dict]:
    """
    从清洗后的 HTML 提取新闻列表。

    每条记录包含：title、url、time。
    """
    soup = BeautifulSoup(cleaned_html, 'html.parser')
    items = []
    for a in soup.find_all('a', href=True):
        href = a.get('href', '')
        if not NEWS_URL_REGEX.search(href):
            continue
        title = a.get_text(strip=True)
        if not title or len(title) <= 5:
            continue
        dm = _DATE_PATH_RE.search(href)
        time_str = f"{dm.group(1)}-{dm.group(2)}-{dm.group(3)}" if dm else ""
        items.append({
            'title': title,
            'url': href if href.startswith('http') else f'https://{href}',
            'time': time_str,
        })
    return items