"""
embedded_json.py - 嵌入式 JSON 解析模块

从原始 HTML 中查找并解析嵌入式 JSON 数据。
"""
import json
import re
from datetime import datetime
from typing import Any


# 常见嵌入式 JSON 关键字
_EMBEDDED_KEYWORDS = [
    "initialNewsList",
    "newsList",
    "articleList",
    "dataList",
    "listData",
    "newsData",
    "__NEXT_DATA__",
]

# Tiptap 编辑器 JSON 关键字（Tiptap 是 Next.js 常用的富文本编辑器）
# 注意：HTML 中的 JSON 使用转义引号，实际字符串序列是: type\":\"link\"
# 在 Python 代码中写作: 'type\\":\\"link'
_TIPTAP_KEYWORDS = [
    'type\\":\\"link',
]


def find_embedded_json(html: str) -> dict | list | None:
    """
    在原始 HTML 中查找嵌入式 JSON。

    Args:
        html: 原始 HTML 字符串

    Returns:
        解析后的 JSON 对象，或 None
    """
    # 优先用专用解析器处理 __NEXT_DATA__（Next.js），避免误匹配 meta 等标签
    next_data = _extract_next_data(html)
    if next_data is not None:
        return next_data

    # 尝试 Tiptap JSON 格式（Next.js 富文本编辑器）
    tiptap_result = _extract_tiptap_json(html)
    if tiptap_result is not None:
        return tiptap_result

    for kw in _EMBEDDED_KEYWORDS:
        if kw in html:
            idx = html.find(kw)
            colon_idx = html.index(":", idx)
            start = colon_idx + 1

            # 跳过空白
            while start < len(html) and html[start] in " \t\n\r":
                start += 1

            if start >= len(html):
                continue

            first_char = html[start]
            if first_char == "[":
                json_str = _extract_array(html, start)
            elif first_char == "{":
                json_str = _extract_object(html, start)
            else:
                continue

            if json_str:
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    continue
    return None


def _extract_next_data(html: str) -> dict | None:
    """
    专用解析器：从 <script id="__NEXT_DATA__"> 标签中提取 Next.js __NEXT_DATA__ JSON。

    与通用关键字查找不同，这个方法精确定位 <script> 标签，避免误匹配 meta 等。
    """
    pattern = '<script id="__NEXT_DATA__"'
    idx = html.find(pattern)
    if idx == -1:
        return None
    gt_idx = html.index(">", idx)
    start = gt_idx + 1
    if start >= len(html):
        return None
    json_str = _extract_object(html, start)
    if json_str:
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass
    return None


def _extract_array(html: str, start: int) -> str | None:
    """提取 JSON 数组"""
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


def _extract_object(html: str, start: int) -> str | None:
    """提取 JSON 对象"""
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


def _extract_tiptap_json(html: str) -> dict | list | None:
    """
    提取 Tiptap 编辑器格式的 JSON。

    Tiptap JSON 格式：含有 "type":"link" 和 "fields":{"url":"..."} 结构。
    智谱 AI 等网站使用 Tiptap 作为富文本编辑器，链接存储在这种格式中。

    HTML 中的 JSON 使用转义引号（\"），例如：
    {"type":"link","version":3,"fields":{"url":"https://..."}}

    Returns:
        包含 url 字段的列表，或 None
    """
    results = []
    seen_urls = set()  # 去重

    for kw in _TIPTAP_KEYWORDS:
        if kw not in html:
            continue

        # 查找所有关键字位置
        idx = 0
        while True:
            idx = html.find(kw, idx)
            if idx == -1:
                break

            # 搜索 forward 从关键字位置找 "fields":{ pattern
            # HTML 中的实际字符串是 \"fields\":{ (escaped quotes)
            fields_pattern = '\\"fields\\":{'
            fields_idx = html.find(fields_pattern, idx)
            if fields_idx == -1:
                idx += 1
                continue

            # 从 fields { 位置提取内层对象
            start = fields_idx + len(fields_pattern) - 1  # position of the {
            depth = 0
            in_string = False
            escape_next = False

            for i in range(start, min(len(html), start + 2000)):
                c = html[i]

                if escape_next:
                    escape_next = False
                    continue

                if c == '\\':
                    escape_next = True
                    continue

                if c == '"':
                    in_string = not in_string
                    continue

                if in_string:
                    continue

                if c == '{':
                    if depth == 0:
                        depth = 1
                    else:
                        depth += 1
                elif c == '}':
                    depth -= 1
                    if depth == 0:
                        json_str = html[start:i + 1]
                        try:
                            unescaped = json_str.replace('\\"', '"')
                            fields_data = json.loads(unescaped)
                            if 'url' in fields_data:
                                url = fields_data['url']
                                # 去重
                                if url in seen_urls:
                                    idx += 1
                                    break
                                seen_urls.add(url)
                                # 过滤：只保留研究文章链接（包含 /blog/ 或 /zh/ 等路径）
                                # 排除外部资源链接（PDF、GitHub、HuggingFace 等）
                                if '/blog/' not in url and '/zh/' not in url and '/research/' not in url:
                                    idx += 1
                                    break
                                title = url.split('/')[-1] if '/' in url else url
                                results.append({'fields': {'url': url, 'text': title}})
                        except json.JSONDecodeError:
                            pass
                        break
            idx += 1

    return results if results else None


def extract_news_items(
    json_data: dict | list,
    url_field: str = "url",
    title_field: str = "title",
    time_field: str = "createTime",
    summary_field: str = "summary",
    date_format: str = None,
) -> list[dict]:
    """
    从 JSON 数据中提取新闻条目。

    Args:
        json_data: JSON 对象（列表或单个对象）
        url_field: URL 字段名
        title_field: 标题字段名
        time_field: 时间字段名
        summary_field: 摘要字段名
        date_format: 日期格式（unix/timestamp/yyyy-MM-dd HH:mm:ss 等）

    Returns:
        新闻条目列表
    """
    items = []

    # 处理 __NEXT_DATA__ 结构（Next.js 页面）
    if isinstance(json_data, dict):
        json_data = _navigate_next_data(json_data)

    if isinstance(json_data, list):
        data_list = json_data
    elif isinstance(json_data, dict):
        #尝试找到列表字段
        for key in ["list", "data", "newsList", "articleList", "items"]:
            if key in json_data and isinstance(json_data[key], list):
                data_list = json_data[key]
                break
        else:
            data_list = [json_data]
    else:
        return []

    for item in data_list:
        if not isinstance(item, dict):
            continue

        # __next_data__ 格式：_navigate_next_data 已展平字段，直接读取
        if date_format == "__next_data__":
            url = item.get("url", "")
            title = item.get("title", "")
            if not url or not title:
                continue
            if not url.startswith("http"):
                url = item.get("link", "") or item.get("href", "")
            news_item = {
                "title": title,
                "url": url,
                "summary": item.get("summary", ""),
                "time": item.get("time", ""),
            }
            items.append(news_item)
            continue

        # 支持嵌套字段（dot notation，如 shareInfo.shareUrl）
        url = _get_nested(item, url_field)
        title = _get_nested(item, title_field)

        if not url or not title:
            continue

        # 跳过非 HTTP 链接
        if not url.startswith("http"):
            url = item.get("link", "") or item.get("href", "")

        time_val = _get_nested(item, time_field) if time_field else ""

        news_item = {
            "title": title,
            "url": url,
            "summary": _get_nested(item, summary_field) if summary_field else "",
            "time": _parse_time(time_val, date_format),
        }
        items.append(news_item)

    return items


def _get_nested(data: dict, path: str) -> Any:
    """支持 dot notation 的嵌套字段读取，如 'shareInfo.shareUrl'"""
    if not path or "." not in path:
        return data.get(path, "")
    keys = path.split(".")
    val = data
    for k in keys:
        if isinstance(val, dict):
            val = val.get(k, "")
        else:
            return ""
    return val


def _navigate_next_data(data: dict) -> dict | list:
    """
    解析 __NEXT_DATA__ 嵌入式 JSON 的嵌套结构。

    典型路径（crawl4ai 渲染后）：pageProps.pageProps.initSsrData.pageInfo.list[].timeList[]
    典型路径（raw_fetch 原始）：props.pageProps.initSsrData.pageInfo.list[].timeList[]
    每条快讯的 dateInfo 包含完整日期信息（年、月、日、时、分）。
    """
    # 尝试两种路径：crawl4ai 渲染（双 pageProps）和 raw_fetch 原始（单 props）
    ssr = None

    # 路径1: pageProps.pageProps（crawl4ai 渲染后的 Next.js）
    page_props = data.get("pageProps", {})
    if isinstance(page_props, dict):
        inner = page_props.get("pageProps", {})
        if isinstance(inner, dict) and "initSsrData" in inner:
            ssr = inner.get("initSsrData", {})

    # 路径2: props.pageProps（raw_fetch 原始 HTML）
    if ssr is None:
        props = data.get("props", {})
        if isinstance(props, dict):
            page_props2 = props.get("pageProps", {})
            if isinstance(page_props2, dict):
                ssr = page_props2.get("initSsrData", {})

    if ssr is None:
        return []

    page_info = ssr.get("pageInfo", {})
    news_list = page_info.get("list", [])

    result = []
    for day_group in news_list:
        if not isinstance(day_group, dict):
            continue
        # timeList 是同一天的快讯数组，每条有 dateInfo（完整日期）和 time（时间）
        time_list = day_group.get("timeList", [])
        for item in time_list:
            if not isinstance(item, dict):
                continue
            # dateInfo 可能在 item 顶层（crawl4ai 渲染后）或 shareInfo 内（raw_fetch）
            date_info = item.get("dateInfo", {}) or {}
            if not date_info:
                share_info = item.get("shareInfo", {}) or {}
                date_info = share_info.get("dateInfo", {}) or {}
            year = date_info.get("year", "")
            month = date_info.get("month", "")
            day = date_info.get("day", "")
            time_str = item.get("time", "")
            # 合成完整 datetime：年-月-日 时:分:秒
            if year and month and day:
                full_date = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                if time_str:
                    full_datetime = f"{full_date} {time_str}:00"
                else:
                    full_datetime = f"{full_date} 00:00:00"
            else:
                full_datetime = time_str

            # 处理标题：优先用 shareInfo.title（更完整），其次 item.title
            share_info = item.get("shareInfo", {}) or {}
            title = share_info.get("title", "") or item.get("title", "") or item.get("name", "")

            # 处理 URL：优先 shareInfo.shareUrl
            url = share_info.get("shareUrl", "") or item.get("url", "")
            if url and not url.startswith("http"):
                url = "https://www.cnstock.com" + url

            news_item = {
                "title": title,
                "url": url,
                "summary": item.get("text", "") or share_info.get("summary", "") or item.get("summary", ""),
                "time": full_datetime,
            }
            result.append(news_item)

    return result


def _parse_time(time_value: Any, date_format: str = None) -> str:
    """解析时间值"""
    if not time_value:
        return ""

    # 已经是字符串
    if isinstance(time_value, str):
        return time_value

    # Unix 时间戳（毫秒）
    if isinstance(time_value, int):
        try:
            dt = datetime.fromtimestamp(time_value / 1000)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, OSError):
            return str(time_value)

    return str(time_value)