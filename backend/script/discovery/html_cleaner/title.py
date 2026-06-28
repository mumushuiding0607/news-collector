"""
title.py - 标题清洗
"""

from __future__ import annotations

import re

from ._constants import (
    MARKDOWN_LINK_RE,
    WHITESPACE_RE,
    BRACKET_TRAILING_RE,
    HEADER_RE,
    ISOLATED_BANG_RE,
    DATE_TRAILING_RE,
    TIME_SUFFIX_RE,
    SOURCE_SUFFIX_RE,
)


def clean_title(title: str) -> str:
    """
    清理标题中的日期、多余空白、markdown 残留、编码损坏。

    移除：
    - 尾部日期后缀
    - 编码损坏（Mojibake）
    - markdown 残留（图片、标题标记）
    - 嵌入 URL 残留
    - 时间/来源后缀（小时前、分钟前、昨天、证券报等）
    """
    # 移除日期后缀
    title = DATE_TRAILING_RE.sub('', title).rstrip()
    title = title.strip().strip('[').strip(']').strip()

    # 修复 GBK/UTF-8 编码损坏
    if '' in title or (title.count('') > 2):
        try:
            recovered = title.encode('utf-8', errors='replace').decode('gbk', errors='replace')
            if recovered and '' not in recovered and len(recovered) >= 5:
                title = recovered
        except Exception:
            pass

    # 移除 markdown 残留
    title = MARKDOWN_LINK_RE.sub('', title)
    title = HEADER_RE.sub(' ', title)
    title = ISOLATED_BANG_RE.sub(' ', title)

    # 移除嵌入 URL 残留
    if '](' in title:
        title = title[:title.rfind('](')].strip()

    # 移除末尾时间/来源标记
    title = TIME_SUFFIX_RE.sub('', title)
    title = SOURCE_SUFFIX_RE.sub('', title)

    title = WHITESPACE_RE.sub(' ', title).strip()
    return title


def clean_candidate(cand: str) -> str:
    """清理标题候选：移除空白和尾部残留（用于中间步骤）"""
    cand = WHITESPACE_RE.sub(' ', cand).strip()
    cand = BRACKET_TRAILING_RE.sub('', cand).strip()
    return cand