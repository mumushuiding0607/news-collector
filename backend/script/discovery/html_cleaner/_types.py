"""
_types.py - 数据结构定义
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class ApiEndpoint:
    """检测到的 API 端点信息"""
    url: str
    method: str
    data_type: str
    params: list
    raw_snippet: str


@dataclass
class CleanedHtml:
    """清洗后的 HTML 结果"""
    html: str
    main_content_tag: str = 'body'
    removed_count: int = 0