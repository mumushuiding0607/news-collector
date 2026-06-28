"""
html_cleaner.py - 兼容垫片

此文件仅用于向后兼容，所有功能已迁移至 html_cleaner 包。
新代码请直接导入：from script.discovery.html_cleaner import ...
"""

from script.discovery.html_cleaner import (
    # 常量
    DATE_REGEX,
    DATE_TRAILING_RE,
    NEWS_URL_REGEX,
    BOILERPLATE_PATTERNS,
    CONTENT_EXTRACT_PATTERNS,
    HTML_EXTRACT_PATTERNS,
    MARKDOWN_LINK_RE,
    WHITESPACE_RE,
    # 数据结构
    ApiEndpoint,
    CleanedHtml,
    # 列表页清洗
    clean_html,
    detect_apis_in_html,
    extract_news_list_from_cleaned,
    is_date_text,
    # 文章正文清洗
    clean_article_html,
    # Boilerplate 清理
    clean_boilerplate_text,
    is_boilerplate_line,
    # 正文内容提取
    extract_content_from_html,
    # 标题清洗
    clean_title,
    clean_candidate,
    # 文章链接提取
    extract_article_links,
    extract_links_from_html,
    # 向后兼容别名
    extract_content_from_html_textutil,
    clean_title_v2,
)

__all__ = [
    # 常量
    'DATE_REGEX', 'DATE_TRAILING_RE', 'NEWS_URL_REGEX',
    'BOILERPLATE_PATTERNS', 'CONTENT_EXTRACT_PATTERNS', 'HTML_EXTRACT_PATTERNS',
    'MARKDOWN_LINK_RE', 'WHITESPACE_RE',
    # 数据结构
    'ApiEndpoint', 'CleanedHtml',
    # 列表页清洗
    'clean_html', 'detect_apis_in_html', 'extract_news_list_from_cleaned', 'is_date_text',
    # 文章正文清洗
    'clean_article_html',
    # Boilerplate 清理
    'clean_boilerplate_text', 'is_boilerplate_line',
    # 正文内容提取
    'extract_content_from_html',
    # 标题清洗
    'clean_title', 'clean_candidate',
    # 文章链接提取
    'extract_article_links', 'extract_links_from_html',
    # 向后兼容
    'extract_content_from_html_textutil', 'clean_title_v2',
]