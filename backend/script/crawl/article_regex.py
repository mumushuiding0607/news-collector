# article_regex.py - URL过滤与预编译正则常量
# 基础设施层：只负责URL验证和正则定义，不涉及业务逻辑

import re

# ---- 从 html_cleaner 导入公共正则常量 ----
from script.discovery.html_cleaner._patterns_a import (
    WHITESPACE_RE,
    HEADER_RE,
    TIME_SUFFIX_RE,
    SOURCE_SUFFIX_RE,
    PLAIN_URL_RE,
    BROKEN_LINK_RE,
    IMG_URL_RE,
    FILE_EXT_RE,
)
# BRACKET_TRAILING_RE 需要单独定义（html_cleaner 用不同模式）
BRACKET_TRAILING_RE = re.compile(r'\s*\]\(\s*$')

# ---- 本地独有模式 ----
IMG_LINK_RE = re.compile(r'!\[[^\]]*\]\([^)]*\)')
PREV_LINE_RE = re.compile(r'^\s*[\]\)>}\-|:：\s\d*[:：\s]*')

# ---- is_article_url 内联正则（预编译避免热路径重复编译）----
_IS_URL_ASSET_RE = re.compile(r'\.(gif|jpg|jpeg|png|webp|svg|ico|css|js|json|woff2?)(\?.*)?$', re.I)
_IS_URL_HTTP_RE = re.compile(r'https?://')
_IS_URL_DIGIT_RE = re.compile(r'/(\d+)')
_IS_URL_DIGIT_HYPHEN_RE = re.compile(r'[-.](\d+)[-.]')

# 非文章URL路径关键字
_NON_ARTICLE_PATHS = ['/node/', '/category/', '/topic/', '/channel/', '/list/', '/index', '/page']
# 文章URL路径关键字
_ARTICLE_PATHS = ['/article/', '/news/', '/info/', '/detail/', '/show/']


# ==================== URL过滤 ====================

def is_article_url(url: str) -> bool:
    """
    判断URL是否为文章页，排除列表页、分类页等非文章URL。
    """
    if _IS_URL_ASSET_RE.search(url):
        return False
    if not _IS_URL_HTTP_RE.match(url):
        return False
    if any(k in url.lower() for k in _NON_ARTICLE_PATHS):
        return False
    digit_segs = _IS_URL_DIGIT_RE.findall(url)
    if not digit_segs:
        digit_segs = _IS_URL_DIGIT_HYPHEN_RE.findall(url)
    if len(digit_segs) >= 1 and url.lower().endswith(('.htm', '.html', '.shtml')):
        return True
    if any(p in url.lower() for p in _ARTICLE_PATHS):
        return True
    return False


def extract_title_from_window(search_window: str) -> str:
    """
    从搜索窗口中提取标题。
    策略：移除图片链接后，找最后一个 ]( 模式，以其 [ 位置划定标题块。
    """
    cleaned = IMG_LINK_RE.sub('', search_window)
    close = cleaned.rfind('](')
    if close < 0:
        return search_window.strip()
    open_bracket = cleaned.rfind('[', 0, close)
    if open_bracket >= 0:
        return cleaned[open_bracket + 1:close].strip()
    return cleaned[:close].strip()