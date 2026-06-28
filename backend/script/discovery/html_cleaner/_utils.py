"""
_utils.py - 统一工具函数
"""

from __future__ import annotations

import html as html_module
import re

from ._patterns import DATE_REGEX, WHITESPACE_RE


# =============================================================================
# 日期判断
# =============================================================================

# 纯时间格式（HH:MM 或 HH:MM:SS），单独短字符串也应识别为日期
_TIME_ONLY_RE = re.compile(r'^\s*\d{1,2}:\d{2}(:\d{2})?\s*$')


def is_date_text(text: str) -> bool:
    """判断文本是否为日期格式"""
    if not text:
        return False
    s = text.strip()
    # 纯时间（HH:MM / HH:MM:SS）即使 < 6 字符也应识别
    if _TIME_ONLY_RE.match(s):
        return True
    if len(s) < 6:
        return False
    return bool(DATE_REGEX.search(s))


# =============================================================================
# 文本规范化
# =============================================================================

def strip_html_tags(html: str) -> str:
    """移除 HTML 标签"""
    return re.sub(r'<[^>]+>', '', html)


def normalize_whitespace(text: str) -> str:
    """规范化空白字符：多个空白合并为一个"""
    return WHITESPACE_RE.sub(' ', text).strip()


def compress_newlines(text: str) -> str:
    """压缩多余换行：3个以上换行压缩为2个"""
    return re.sub(r'\n{3,}', '\n\n', text)


def html_to_text(html: str) -> str:
    """HTML 转纯文本：移除标签 + 反转义 + 规范化空白"""
    text = strip_html_tags(html)
    text = html_module.unescape(text)
    text = normalize_whitespace(text)
    return text


# =============================================================================
# Markdown 清理
# =============================================================================

# Markdown 清理正则列表
_MARKDOWN_CLEAN_PATTERNS = [
    (re.compile(r'\*\*([^\*]+)\*\*'), r'\1'),   # 加粗 **text** -> text
    (re.compile(r'\*([^*]+)\*'), r'\1'),         # 斜体 *text* -> text
    (re.compile(r'__([^_]+)__'), r'\1'),         # 加粗 __text__ -> text
    (re.compile(r'_([^_]+)_'), r'\1'),           # 斜体 _text_ -> text
    (re.compile(r'~~([^~]+)~~'), r'\1'),         # 删除线 ~~text~~ -> text
    (re.compile(r'`([^`]+)`'), r'\1'),           # 行内代码 `text` -> text
    (re.compile(r'!\[([^\]]*)\]\([^)]*\)'), ''), # 图片 ![text](url) -> 删除
    (re.compile(r'\[([^\]]+)\]\([^)]*\)'), r'\1'),  # 链接 [text](url) -> text
    (re.compile(r'#{1,6}\s+'), ''),              # 标题 # text -> text
]


def clean_markdown_text(text: str) -> str:
    """
    清理 Markdown 格式，移除样式残留。

    移除：加粗、斜体、删除线、行内代码、图片、链接文字、标题标记
    规范化：空白字符、多余换行
    """
    for pat, repl in _MARKDOWN_CLEAN_PATTERNS:
        text = pat.sub(repl, text)
    text = normalize_whitespace(text)
    text = compress_newlines(text)
    return text.strip()