"""
textutil.py - 文章内容质量检查与提取

核心职责：文章质量检查。

正文提取和 Boilerplate 清理已迁移到：
  from script.discovery.html_cleaner import (
      extract_content_from_html,
      clean_boilerplate_text,
      BOILERPLATE_PATTERNS,
  )
"""

import re


def check_article_quality(title: str, content: str, publish_time: str | None) -> dict:
    """检查文章内容质量，返回报告字典"""
    report = {
        "passed": True,
        "issues": [],
        "content_length": len(content),
        "title_length": len(title),
        "has_time": publish_time is not None,
        "time_is_zero": False,
    }
    if len(content) < 200:
        report["passed"] = False
        report["issues"].append(f"content_too_short:{len(content)}")
    if not title or len(title) < 5:
        report["passed"] = False
        report["issues"].append("title_missing_or_too_short")
    if publish_time:
        time_part = publish_time.split(" ")[1] if " " in publish_time else ""
        if time_part == "00:00:00":
            report["time_is_zero"] = True
            report["issues"].append("time_may_be_missing")
    noise_patterns = [
        r'^[\[【]?(组图|图集|专辑|专题|专栏|视频|图片|海报)[】\]]',
        r'^!\[.*?\]\(',
        r'^[|\-=]{3,}',
        r'^\d+$',
    ]
    for pat in noise_patterns:
        if re.match(pat, title.strip()):
            report["passed"] = False
            report["issues"].append(f"noise_title:{pat}")
            break
    label_chars = content.count('<') + content.count('>') + content.count('{')
    if label_chars > len(content) * 0.05:
        report["passed"] = False
        report["issues"].append(f"content_impure:label_chars={label_chars}")
    return report


# 正文提取已迁移到 html_cleaner.py，保留向后兼容导入
from script.discovery.html_cleaner import extract_content_from_html
