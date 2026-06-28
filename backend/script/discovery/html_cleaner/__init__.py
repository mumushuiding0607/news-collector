"""
html_cleaner package - 统一 HTML 清洗模块

拆分自 discovery/html_cleaner.py，按职责分为：
  - _constants.py  : 正则模式常量
  - _types.py      : 数据结构
  - list_page.py   : 列表页清洗
  - article.py     : 文章正文 HTML 清洗（clean_article_html）
  - boilerplate.py : Boilerplate 清理
  - content.py     : 正文内容提取（正则兜底）
  - title.py       : 标题清洗
  - article_link.py: 文章链接提取

正文提取统一使用 clean_article_html + _extract_text_from_cleaned + _strip_trailing_disclaimer。

使用方式：
  from script.discovery.html_cleaner import (
      # 列表页清洗
      clean_html, detect_apis_in_html,
      # 文章正文清洗
      clean_article_html,
      # Boilerplate 清理
      clean_boilerplate_text, is_boilerplate_line,
      # 文章链接提取
      extract_article_links,
      # 标题清洗
      clean_title,
      # 导出常量
      CONTENT_EXTRACT_PATTERNS, BOILERPLATE_PATTERNS,
  )
"""

from __future__ import annotations

# ---- 工具函数 ----
from ._utils import (
    is_date_text,
    strip_html_tags,
    normalize_whitespace,
    compress_newlines,
    html_to_text,
    clean_markdown_text,
)

# ---- 常量 ----
from ._constants import (
    DATE_REGEX,
    DATE_TRAILING_RE,
    NEWS_URL_REGEX,
    BOILERPLATE_PATTERNS,
    CONTENT_EXTRACT_PATTERNS,
    HTML_EXTRACT_PATTERNS,
    MARKDOWN_LINK_RE,
    WHITESPACE_RE,
)

# ---- 数据结构 ----
from ._types import ApiEndpoint, CleanedHtml

# ---- 列表页清洗 ----
from .list_page import clean_html, extract_news_list_from_cleaned
from ._api_detector import detect_apis_in_html

# ---- 文章正文清洗 ----
from .article import (
    clean_article_html,
)

# ---- Boilerplate 清理 ----
from .boilerplate import (
    clean_boilerplate_text,
    is_boilerplate_line,
)

# ---- 正文内容提取 ----
from .content import (
    extract_content_from_html,
)

# ---- 标题清洗 ----
from .title import (
    clean_title,
    clean_candidate,
)

# ---- 文章链接提取 ----
from .article_link import (
    extract_article_links,
    extract_links_from_html,
)

# =============================================================================
# 向后兼容别名（旧模块路径 → 新入口）
# =============================================================================
extract_content_from_html_textutil = extract_content_from_html
clean_title_v2 = clean_title