"""
util.py - Common utilities (backward-compatible shim)

将大型工具函数拆分到专用模块：
  - datetimeutil.py   - 日期时间解析
  - textutil.py       - 文本内容提取
"""

import re as _re

from datetime import datetime, date

# 导出所有公用 API（保持向后兼容）
from script.common.datetimeutil import (
    parse_publish_time,
    is_today,
    extract_date_from_url,
    extract_date_from_html,
    get_publish_time_extract,
    extract_date_by_pattern,
    DATETIME_REGEX,
    DATE_TRAILING_REGEX,
    DATETIME_PATTERNS,
)

from script.common.textutil import (
    check_article_quality,
    extract_content_from_html,
)

__all__ = [
    "parse_publish_time",
    "is_today",
    "extract_date_from_url",
    "extract_date_from_html",
    "get_publish_time_extract",
    "extract_date_by_pattern",
    "check_article_quality",
    "extract_content_from_html",
    "DATETIME_REGEX",
    "DATE_TRAILING_REGEX",
    "DATETIME_PATTERNS",
]

# COMBINED_DATE_REGEX 已迁移到 datetimeutil.py，统一从那里引用