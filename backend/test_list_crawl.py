import sys, io, asyncio
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from script.db.db_selector import ensure_db
ensure_db('AI新闻')

# 重新加载 crawl_config（确保缓存是基于 AI新闻 的 ContextVar）
import script.crawl.crawl_config as cc
cc._cached_config = None

from script.db.sources_db import get_crawl_config_by_url
from script.common.jsonutil import parse_json_field
from script.discovery.util.html_fetch import fetch_list_html
from script.discovery.html_cleaner import clean_html
from script.crawl.news_list.html_list import extract_list_articles
from script.crawl.crawl_config import get_crawl_config
from script.common.datetimeutil import is_within_days
from datetime import datetime

cfg = get_crawl_config_by_url('http://hy.tencent.com/research')
list_config = parse_json_field(cfg.get('list_config', ''))
crawl_cfg = get_crawl_config()
title_min_len = crawl_cfg.get('titleMinLength', 4)
days = crawl_cfg.get('days', 7)

print(f"titleMinLength: {title_min_len}, days: {days}")

result = asyncio.run(fetch_list_html('http://hy.tencent.com/research'))
html = result[1]
cleaned = clean_html(html)
items = extract_list_articles(cleaned.html, '', '腾讯研究院', list_config, title_min_len, 'http://hy.tencent.com/research')

print(f"Extracted {len(items)} items")
for item in items:
    title = item.get('title', '')
    pub_time = item.get('time', '') or item.get('publish_time', '')
    is_recent = is_within_days(pub_time, days) if pub_time else False
    print(f"  [{is_recent}] {pub_time}: {title[:40]}")
