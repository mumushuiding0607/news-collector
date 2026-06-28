# json_extractor.py - HTML 内嵌 JSON 提取工具
#
# 从原始 HTML 中提取嵌入式 JSON 数据。
# 支持数组和对象两种 JSON 格式，使用深度计数法处理嵌套。
#
# 使用方式：
#   from script.discovery.util.json_extractor import find_embedded_json, extract_json_array, extract_json_object

import json
import re

# 常见嵌入式 JSON 关键字
EMBEDDED_JSON_KEYWORDS = [
    "initialNewsList",
    "newsList",
    "articleList",
    "dataList",
    "listData",
    "newsData",
    "__NEXT_DATA__",
]


def extract_json_array(html: str, start: int) -> str | None:
    """
    从 HTML 中指定位置开始提取 JSON 数组。

    使用深度计数法处理嵌套，支持转义字符。

    Args:
        html: HTML 原始字符串
        start: JSON 数组开始的索引（指向 '['）

    Returns:
        JSON 字符串（含括号），或 None
    """
    depth = 0
    first_open = -1
    end = -1
    in_string = False
    escape_next = False

    for i in range(start, len(html)):
        c = html[i]

        if escape_next:
            escape_next = False
            continue

        if c == "\\":
            escape_next = True
            continue

        if c == '"' and not escape_next:
            in_string = not in_string
            continue

        if in_string:
            continue

        if c == "[" and first_open == -1:
            first_open = i
            depth = 1
        elif c == "[":
            depth += 1
        elif c == "]":
            depth -= 1
            if depth == 0 and first_open != -1:
                end = i
                break

    if first_open == -1 or end == -1:
        return None

    return html[first_open:end + 1]


def extract_json_object(html: str, start: int) -> str | None:
    """
    从 HTML 中指定位置开始提取 JSON 对象。

    使用深度计数法处理嵌套，支持转义字符。

    Args:
        html: HTML 原始字符串
        start: JSON 对象开始的索引（指向 '{'）

    Returns:
        JSON 字符串（含括号），或 None
    """
    depth = 0
    first_open = -1
    end = -1
    in_string = False
    escape_next = False

    for i in range(start, len(html)):
        c = html[i]

        if escape_next:
            escape_next = False
            continue

        if c == "\\":
            escape_next = True
            continue

        if c == '"' and not escape_next:
            in_string = not in_string
            continue

        if in_string:
            continue

        if c == "{" and first_open == -1:
            first_open = i
            depth = 1
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0 and first_open != -1:
                end = i
                break

    if first_open == -1 or end == -1:
        return None

    return html[first_open:end + 1]


def find_embedded_json(html: str, keywords: list[str] = None) -> dict | list | None:
    """
    在原始 HTML 中查找嵌入式 JSON。

    扫描关键字，找到后用深度计数法提取完整 JSON。

    Args:
        html: 原始 HTML 字符串
        keywords: 要扫描的关键字列表（默认使用 EMBEDDED_JSON_KEYWORDS）

    Returns:
        解析后的 JSON 对象/数组，或 None
    """
    if keywords is None:
        keywords = EMBEDDED_JSON_KEYWORDS

    for kw in keywords:
        idx = html.find(kw)
        if idx == -1:
            continue
        try:
            colon_idx = html.index(":", idx)
        except ValueError:
            continue

        start = colon_idx + 1

        # 跳过空白
        while start < len(html) and html[start] in " \t\n\r":
            start += 1

        if start >= len(html):
            continue

        first_char = html[start]
        if first_char == "[":
            json_str = extract_json_array(html, start)
        elif first_char == "{":
            json_str = extract_json_object(html, start)
        else:
            continue

        if json_str:
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                continue

    return None