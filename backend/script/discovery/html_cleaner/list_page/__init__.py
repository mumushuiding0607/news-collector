"""
list_page - 列表页 HTML 清洗

按 4 步流水线清洗列表页 HTML：
    1. 清理无用属性
    2. 提取新闻容器
    3. 补充日期/时间元素（位于新闻容器外的日期选择器等）
    4. 组装清洗后 HTML
    5. 移除空元素和非文本元素
"""
from __future__ import annotations

from bs4 import BeautifulSoup

from .._constants import _ATTR_REMOVE_LINKLESS_RE, _ATTR_REMOVE_RE
from .._types import CleanedHtml
from ._containers import extract_news_containers
from ._extract import extract_news_list_from_cleaned
from ._pruning import remove_empty_and_nontext_elements


def _clean_attributes(html: str, remove_links: bool = False) -> str:
    """删除 HTML 无用属性，只保留 class, id, href, src, data-*, value, type, name"""
    if remove_links:
        return _ATTR_REMOVE_LINKLESS_RE.sub('', html)
    return _ATTR_REMOVE_RE.sub('', html)


def _find_datetime_elements(html: str) -> list[str]:
    """从 HTML 中提取含日期/时间属性的元素（日期选择器等），防止被丢失"""
    from script.common.datetimeutil import DATETIME_REGEX

    soup = BeautifulSoup(html, 'html.parser')
    datetime_elements = []
    seen = set()

    for tag in soup.find_all(True):
        if tag.name in ('html', 'head', 'body'):
            continue
        # 检查 value 属性中是否包含日期时间
        value = tag.get('value', '')
        if value and DATETIME_REGEX.search(str(value)):
            tag_str = str(tag)
            if tag_str not in seen:
                seen.add(tag_str)
                datetime_elements.append(tag_str)
            continue
        # 检查 data-* 属性中是否包含日期时间
        for attr_val in tag.attrs.values():
            val_str = str(attr_val) if not isinstance(attr_val, str) else attr_val
            if isinstance(attr_val, list):
                val_str = ' '.join(str(v) for v in attr_val)
            if DATETIME_REGEX.search(val_str):
                tag_str = str(tag)
                if tag_str not in seen:
                    seen.add(tag_str)
                    datetime_elements.append(tag_str)
                break

    return datetime_elements


def _remove_useless(html: str, remove_links: bool = False) -> str:
    """先清理属性，再提取新闻容器，再补充日期元素，再组装清洗后 HTML"""
    # Step 1: 清理整个 HTML 的属性
    cleaned_html = _clean_attributes(html, remove_links)

    # Step 2: 从清理后的 HTML 提取新闻容器
    containers = extract_news_containers(cleaned_html)

    # Step 3: 补充日期/时间元素（日期选择器等）
    datetime_elements = _find_datetime_elements(html)

    # Step 4: 组装清洗后 HTML
    parts = ['<!DOCTYPE html>', '<html>', '<head></head>', '<body>']
    parts.extend(containers)
    parts.extend(datetime_elements)
    parts.extend(['</body>', '</html>'])
    assembled = '\n'.join(parts)

    # Step 5: 移除空元素和非文本元素
    return remove_empty_and_nontext_elements(assembled)


def clean_html(html: str, remove_links: bool = False) -> CleanedHtml:
    """清洗列表页 HTML，移除无用内容。"""
    cleaned_str = _remove_useless(html, remove_links)

    orig_soup = BeautifulSoup(html, 'html.parser')
    clean_soup = BeautifulSoup(cleaned_str, 'html.parser')
    removed = len(list(orig_soup.find_all(True))) - len(list(clean_soup.find_all(True)))

    return CleanedHtml(
        html=cleaned_str,
        main_content_tag='body',
        removed_count=removed
    )


__all__ = ["clean_html", "extract_news_list_from_cleaned"]
