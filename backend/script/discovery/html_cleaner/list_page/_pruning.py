# _pruning.py - 移除无用元素
#
# 在已组装好的 HTML 中迭代移除无用元素：短文本无日期/无新闻链接的节点。

import re
from bs4 import BeautifulSoup

from script.common.datetimeutil import DATETIME_REGEX
from .._constants import NEWS_URL_REGEX

# 完全无用的非文本元素
_NON_TEXT_TAGS = {'img', 'svg', 'canvas', 'audio', 'video', 'iframe', 'source', 'track'}

# 中文字符范围
_CHINESE_RE = re.compile(r'[一-鿿]')


def _count_chinese(text: str) -> int:
    """统计文本中中文字符数量"""
    return len(_CHINESE_RE.findall(text))


def remove_empty_and_nontext_elements(html: str) -> str:
    """
    移除无用元素（贪婪模式）：
    1. 非文本元素（img、svg、canvas 等）
    2. script、style、HTML 注释
    3. 字符数 < 10 且不是日期/时间格式的 DOM 元素（连同后代一起移除）
    """
    soup = BeautifulSoup(html, 'html.parser')

    # 移除非文本元素
    for tag in soup.find_all(_NON_TEXT_TAGS):
        tag.decompose()

    # 移除 script、style、注释
    for tag in soup.find_all(['script', 'style']):
        tag.decompose()
    # 移除 HTML 注释元素（<!-- ... -->），但不要移除作为文本内容的 Comment 对象
    from bs4 import Comment
    for tag in soup.find_all(True):
        if hasattr(tag, 'children'):
            for child in list(tag.children):
                if isinstance(child, Comment):
                    child.extract()
    # 移除纯文本形式的注释（不在 Tag 下）
    for tag in soup.find_all(True):
        if hasattr(tag, 'children'):
            for child in list(tag.children):
                if hasattr(child, 'name') and child.name is None and isinstance(child, str) and '<!--' in child:
                    child.extract()

    # 贪婪模式：一次性移除所有无用元素，不逐个迭代
    tags_to_remove = [tag for tag in soup.find_all() if _is_useless_element(tag)]
    for tag in tags_to_remove:
        tag.decompose()

    return str(soup)


def _is_useless_element(tag) -> bool:
    """
    判断元素是否应该被移除。

    保留条件（满足任一即保留）：
    - 自身中文字符数 >= 10
    - 自身文本是日期/时间格式
    - 属性中包含日期
    - 包含直接新闻链接的后代（<a href="新闻URL">）且 own_text 长度足以构成新闻项
    - 有有意义的子元素

    移除条件：
    - 自身中文字符数 < 10 且不是日期/时间格式 且 无有意义的子元素
    """
    if not hasattr(tag, 'children'):
        return True
    if tag.name in _NON_TEXT_TAGS:
        return True

    # 获取自身文本（不包含后代）
    own_text = tag.get_text(strip=True, separator='')
    chinese_count = _count_chinese(own_text)

    # 结构化标签（li/tr/article/section）作为最小新闻项容器，
    # 其 own_text 应包含完整新闻标题。< 10 中文字符 → 新闻项无效，应移除。
    # 这避免了"《第一时间》 20260615 1/2"这种节目整期链接被当作新闻保留。
    is_structural_item = tag.name in ('li', 'tr', 'article', 'section')

    # 包含新闻链接 → 保留（不受 own_text 字符数影响）
    if _has_news_link_in_descendants(tag):
        return False

    # 中文字符数 >= 10 → 保留（中文网站）
    if chinese_count >= 10:
        return False

    # 纯英文/其他字符：文本长度足够（>= 15 字符）认为是有意义文本
    if len(own_text) >= 15:
        return False

    # 自身文本是日期/时间格式 → 保留
    if own_text and DATETIME_REGEX.search(own_text):
        return False

    # 属性中包含日期 → 保留
    if _has_datetime_in_attrs(tag):
        return False

    # input 标签的 value 属性含日期时间 → 保留（如日期选择器）
    if tag.name == 'input' and tag.get('value') and DATETIME_REGEX.search(str(tag.get('value'))):
        return False

    # 自身是新闻链接容器（<a href="新闻URL">）→ 保留
    if tag.name == 'a' and NEWS_URL_REGEX.search(tag.get('href', '')):
        return False

    # 检查是否有有意义的子元素
    for child in tag.children:
        if child.name is None or child.name in ['\n', '\r', '\t']:
            continue
        if not _is_useless_element(child):
            return False

    # 所有子元素都是无用的（短文本/空白）→ 移除
    return True


def _contains_datetime(tag) -> bool:
    """元素文本是否包含日期/时间"""
    text = tag.get_text()
    return bool(DATETIME_REGEX.search(text)) if text else False


def _has_datetime_in_attrs(tag) -> bool:
    """属性值中是否包含日期/时间"""
    for attr_values in tag.attrs.values():
        if isinstance(attr_values, list):
            for av in attr_values:
                if DATETIME_REGEX.search(av):
                    return True
        elif isinstance(attr_values, str):
            if DATETIME_REGEX.search(attr_values):
                return True
    return False


def _has_news_link(tag) -> bool:
    """元素内是否包含新闻链接"""
    for a in tag.find_all('a', href=True):
        if NEWS_URL_REGEX.search(a.get('href', '')):
            return True
    return False


def _has_news_link_in_descendants(tag) -> bool:
    """元素后代中是否包含新闻链接"""
    for child in tag.descendants:
        if hasattr(child, 'name') and child.name == 'a':
            if NEWS_URL_REGEX.search(child.get('href', '')):
                return True
    return False


def _has_direct_news_link_child(tag) -> bool:
    """元素的直接子元素中是否包含新闻链接"""
    for child in tag.children:
        if hasattr(child, 'name') and child.name == 'a':
            if NEWS_URL_REGEX.search(child.get('href', '')):
                return True
    return False