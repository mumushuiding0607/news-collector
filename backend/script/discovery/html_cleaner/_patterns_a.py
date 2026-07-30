"""
_patterns_a.py - 正则模式常量（基础）
"""

from __future__ import annotations

import re
from script.common.datetimeutil import DATETIME_REGEX, DATE_TRAILING_REGEX

# =============================================================================
# 日期时间
# =============================================================================
DATE_REGEX = DATETIME_REGEX
DATE_TRAILING_RE = DATE_TRAILING_REGEX

# =============================================================================
# 新闻 URL
# =============================================================================
NEWS_URL_PATTERNS = [
    r'/\d{4}[-/]\d{2}[-/]\d{2}',  # 标准日期路径: /2024/01/15/ 或 /2024-01-15/
    r'/20\d{6}[-/]',  # 紧凑日期格式: /20260611/ 或 /20260611-xxx/
    r'/news/[a-zA-Z0-9]+',  # /news/12345 或 /news/abc123
    r'/article/[a-zA-Z0-9]+',  # /article/12345 或 /article/4RwaO2FAacf
    r'/item/[a-zA-Z0-9]+',  # /item/12345 或 /item/abc123
    r'/p/[a-zA-Z0-9]+',  # /p/12345 或 /p/abc123
    r'/id/[a-zA-Z0-9]+',  # /id/12345 或 /id/abc123
    r'/post/[a-zA-Z0-9]+',  # /post/12345 或 /post/abc123
    r'/topic/[a-zA-Z0-9]+',  # /topic/12345 或 /topic/abc123
    r'/info/[a-zA-Z0-9]+',  # /info/12345 或 /info/abc123
    r'/detail/[a-zA-Z0-9]+',  # /detail/12345 或 /detail/abc123
    r'/c\d+',  # 同花顺风格文章ID如 /c677377306
    r'/newsinfo/[a-zA-Z0-9]+',  # csia.net.cn 等
    r'/\d{4}[-/]\d{2}[-/]\d{2}[^/]*\.htm',  # /2024/01/15/news.htm 或 /2024-01-15/news.htm
    r'/\d{8}-[a-zA-Z0-9]+\.html',  # detail-20210524-1820254.html 格式（ID部分支持字母数字）
    r'detail-\d{8}-[a-zA-Z0-9]+\.html',  # detail-20210524-1820254.html（无前导/）
    r'/html/\d{4}/\d{4}/',  # /html/2022/1207/xxx.html 格式
    r'/\d+/\d+/\d+\.htm',  # /1/850/850982.htm 或 /1/1129/1129586.htm 格式
    r'/themeDetails/\d+',  # 华创证券等券商平台文章详情页
]
NEWS_URL_REGEX = re.compile('|'.join(NEWS_URL_PATTERNS), re.IGNORECASE)

# =============================================================================
# API script
# =============================================================================
API_PATTERNS = [
    r'/api/',
    r'\.ajax\s*\(',
    r'fetch\s*\(',
    r'axios\.[a-z]+\(',
    r'XMLHttpRequest',
    r'Request\s*\(',
    r'getJSON\s*\(',
    r"url\s*:\s*['\"][^'\"]*api",
    r"apiUrl\s*[:=]",
    r'http[s]?://[^"\']+/api/',
]
API_SCRIPT_PATTERN = re.compile('|'.join(API_PATTERNS), re.IGNORECASE)

# =============================================================================
# Markdown/URL 链接
# =============================================================================
MARKDOWN_LINK_RE = re.compile(r'!\[[^\]]*\]\([^)]*\)')
WHITESPACE_RE = re.compile(r'\s+')
BRACKET_TRAILING_RE = re.compile(r'\s*\]\(\s*$')
PLAIN_URL_RE = re.compile(
    r'https?://[^\s\)\]"\'<>]{20,200}?\.(?:s?html?|htm)(?:\?[^\s<]*)?', re.I
)
BROKEN_LINK_RE = re.compile(r'([^\]\n]{3,50})\]\((https?://[^\)]+)\)(?:\s|$)', re.I)
IMG_URL_RE = re.compile(r'\.(jpg|jpeg|png|gif|webp|svg|ico)(\?|$)', re.I)
FILE_EXT_RE = re.compile(r'\.(jpg|jpeg|png|shtml?|html?|php|asp)(\?|$)', re.I)

# =============================================================================
# 标题清洗
# =============================================================================
TIME_SUFFIX_RE = re.compile(r'\s+[^\s]{2,10}(?:小时前|分钟前|昨天|前天)\S*\s*$')
SOURCE_SUFFIX_RE = re.compile(
    r'\s+[^\s]{2,6}(?:证券报|基金报|经济报道|同花顺|华尔街见闻|数据宝|券商中国|财闻)\S*\s*$'
)
HEADER_RE = re.compile(r'\s*####?\s*')
ISOLATED_BANG_RE = re.compile(r'\s*!\s*')

# =============================================================================
# 文章内容区域匹配
# =============================================================================
_ARTICLE_TITLE_RE = re.compile(r'article[_ ]?content[_ ]?title', re.I)
_TIME_CLASS_RE = re.compile(r'time', re.I)
_DETAIL_CONTENT_RE = re.compile(r'detail[_]?content', re.I)
_ARTICLE_CONTENT_RE = re.compile(r'article[_ ]?content', re.I)
_CONTENT_CLASS_RE = re.compile(r'content', re.I)