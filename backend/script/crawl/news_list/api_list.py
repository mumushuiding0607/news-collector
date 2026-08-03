"""
api_list.py - API类型数据源采集

通用 API 采集（批量入库）:
- fetch_api_page: 调用 API 获取单页数据
- crawl_api_source: 根据 list_config 采集 API 数据源
- _crawl_generic_api: 通用 API 采集逻辑
- _extract_items_from_response: 从 API 响应中提取数据列表
"""
import json
import re
import urllib.request
from datetime import date

from script.log import log as _log
from script.common.jsonutil import parse_json_field
from script.common.datetimeutil import format_date_by_format, is_today, is_within_days
from script.bootstrap import is_ai_news_db


def log(msg: str):
    _log("list_crawler", msg)


# ========== 通用 API ==========


def fetch_api_page(endpoint: str, params: dict, page: int = 1) -> dict:
    """调用 API 获取单页数据"""
    # 修复协议相对 URL（//api.cntv.cn/... → https://api.cntv.cn/...）
    if endpoint.startswith("//"):
        endpoint = "https:" + endpoint

    all_params = {**params, "p": page}
    query = "&".join(f"{k}={v}" for k, v in all_params.items())
    url = f"{endpoint}?{query}" if "?" not in endpoint else f"{endpoint}&{query}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        log(f"API 请求失败: {e}")
        return {}


def crawl_api_source(source: dict, batch_id: int, target_date: date | None = None) -> dict:
    """根据 list_config 采集 API 数据源"""
    name = source.get("name", source.get("config_name", "未知数据源"))
    list_config_str = source.get("list_config")

    if not list_config_str:
        log(f"{name}: 无 list_config 配置")
        return {"today": 0, "error": "no_list_config"}

    list_config = parse_json_field(list_config_str)
    if not list_config:
        log(f"{name}: list_config 为空")
        return {"today": 0, "error": "empty_list_config"}

    api_type = list_config.get("type", "api")
    # 归一化类型名称
    if api_type in ("ajax", "fetch", "xmlhttp"):
        api_type = "api"

    if api_type == "api" or api_type == "ajax" or api_type == "fetch" or api_type == "xmlhttp" or api_type == "column" or api_type == "cctv":
        return _crawl_generic_api(source, batch_id, target_date, list_config)
    else:
        log(f"{name}: 不支持的 API 类型: {api_type}")
        return {"today": 0, "error": f"unsupported_type: {api_type}"}


def fetch_api_items(source: dict, target_date: date | None = None) -> list[dict]:
    """从 API 数据源拉取当天 items（不写入数据库），供 /api/news/fetch 等预览接口使用。

    支持两种配置格式：
    - 新格式（api_url + url_field/title_field/...）：直接字段名提取，url_template 构造 URL
    - 旧格式（endpoint + field_mapping）：通过 field_mapping 映射字段

    Returns:
        list[dict]，每个 dict 含 title/url/summary/date（与 _crawl_generic_api 入库前一致）。
    """
    name = source.get("name", source.get("config_name", "未知数据源"))
    list_config_str = source.get("list_config")
    if not list_config_str:
        log(f"{name}: 无 list_config 配置")
        return []
    list_config = parse_json_field(list_config_str)
    if not list_config:
        return []

    # 区分新旧格式：新格式用 api_url，旧格式用 endpoint
    api_url = list_config.get("api_url") or list_config.get("endpoint", "")
    if not api_url:
        log(f"{name}: 无 api_url/endpoint")
        return []

    is_new_format = bool(list_config.get("api_url"))

    if is_new_format:
        return _fetch_api_items_new_format(source, target_date, list_config)
    else:
        return _fetch_api_items_old_format(source, target_date, list_config)


def _fetch_api_items_new_format(source: dict, target_date: date | None, list_config: dict) -> list[dict]:
    """新格式 API 采集：api_url + url_field/url_template + 各字段名直接提取"""
    name = source.get("name", source.get("config_name", "未知数据源"))
    api_url = list_config["api_url"]
    url_template = list_config.get("url_template", "")
    url_field = list_config.get("url_field", "url")
    title_field = list_config.get("title_field", "title")
    time_field = list_config.get("time_field", "publishedAt")
    content_field = list_config.get("content_field", "content")
    page_param = list_config.get("page_param", "page")
    per_param = list_config.get("per_param", "per")
    per_default = list_config.get("per_default", 20)
    date_format = list_config.get("date_format", "YYYY/MM/DD HH:mm")

    if target_date is None:
        target_date = date.today()

    # 构建初始参数（去掉日期过滤，机器之心 API 不支持日期参数）
    params = {}
    if per_param:
        params[per_param] = per_default

    all_items = []
    page = 1
    max_pages = list_config.get("max_pages", 5)

    while page <= max_pages:
        params = dict(params)
        params[page_param] = page
        data = _fetch_api_page(api_url, params)
        if not data:
            break

        # 新格式：直接在顶层 articles 数组
        items = data if isinstance(data, list) else data.get("articles", [])
        if not items:
            break

        for item in items:
            # 构造 URL
            raw_url = item.get(url_field, "")
            if raw_url and url_template:
                url = url_template.format(slug=raw_url)
            elif raw_url:
                url = raw_url
            else:
                url = ""

            all_items.append({
                "title": item.get(title_field, ""),
                "url": url,
                "date": item.get(time_field, ""),
                "summary": "",
                "content": item.get(content_field, ""),
            })
        page += 1

    # 过滤当天
    today_items = _filter_today_items_new_format(all_items, list_config, target_date)
    return [
        {
            "title": it.get("title", ""),
            "url": it.get("url", ""),
            "summary": it.get("summary", ""),
            "time": it.get("date", ""),
            "publish_time": it.get("date", ""),
        }
        for it in today_items
    ]


def _filter_today_items_new_format(all_items: list, list_config: dict, target_date: date) -> list:
    """过滤当天 items（新格式，AI新闻支持3天范围）"""
    time_field = list_config.get("time_field", "publishedAt")
    date_format = list_config.get("date_format", "YYYY/MM/DD HH:mm")
    days = 3 if is_ai_news_db() else 0
    return [
        it for it in all_items
        if is_within_days(str(it.get("date", "")), today_date=target_date, days=days)
    ]


def _fetch_api_items_old_format(source: dict, target_date: date | None, list_config: dict) -> list[dict]:
    """旧格式 API 采集：endpoint + params + field_mapping"""
    name = source.get("name", source.get("config_name", "未知数据源"))
    endpoint = list_config.get("endpoint", "")
    params = dict(list_config.get("params", {}))
    field_mapping = list_config.get("field_mapping", {})
    pagination = list_config.get("pagination", {})

    column_id = list_config.get("column_id")
    if column_id:
        current_id = params.get("id", "")
        if current_id in ("topicID", "", None) or "placeholder" in str(current_id).lower():
            params["id"] = column_id

    if target_date is None:
        target_date = date.today()
    _inject_date_param(params, list_config, target_date)

    all_items = []
    page = 1
    max_pages = pagination.get("max_pages", 10)
    while page <= max_pages:
        data = fetch_api_page(endpoint, params, page)
        if not data:
            break
        items = _extract_items_from_response(data, field_mapping)
        if not items:
            break
        all_items.extend(items)
        page += 1

    today_items = _filter_today_items_old_format(all_items, field_mapping, list_config, target_date)
    return [
        {
            "title": it.get("title", ""),
            "url": it.get("url", ""),
            "summary": it.get("summary", ""),
            "time": it.get("date", ""),
            "publish_time": it.get("date", ""),
        }
        for it in today_items
    ]


def _filter_today_items_old_format(all_items: list, field_mapping: dict, list_config: dict, target_date: date) -> list:
    days = 3 if is_ai_news_db() else 0
    return [
        it for it in all_items
        if is_within_days(str(it.get("date", "")), today_date=target_date, days=days)
    ]


def _fetch_api_page(endpoint: str, params: dict) -> dict:
    """调用 API 获取单页数据（新格式，不自动加 p 参数）"""
    if endpoint.startswith("//"):
        endpoint = "https:" + endpoint
    query = "&".join(f"{k}={v}" for k, v in params.items())
    url = f"{endpoint}?{query}" if "?" not in endpoint else f"{endpoint}&{query}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        log(f"API 请求失败: {e}")
        return {}


def _crawl_generic_api(source: dict, batch_id: int, target_date: date | None, list_config: dict) -> dict:
    """通用 API 采集（批量入库）"""
    name = source.get("name", source.get("config_name", "未知数据源"))
    endpoint = list_config.get("endpoint", "")
    params = dict(list_config.get("params", {}))
    field_mapping = list_config.get("field_mapping", {})
    pagination = list_config.get("pagination", {})

    if not endpoint:
        log(f"{name}: 无 endpoint")
        return {"today": 0, "error": "no_endpoint"}

    log(f"\n-> API: {name} ({endpoint})")

    # 处理 column_id：如果 config 中有 column_id，且 params.id 是占位符，则替换
    column_id = list_config.get("column_id")
    if column_id:
        current_id = params.get("id", "")
        if current_id in ("topicID", "", None) or "placeholder" in str(current_id).lower():
            params["id"] = column_id

    # 替换日期参数为 target_date
    if target_date is None:
        target_date = date.today()
    _inject_date_param(params, list_config, target_date)

    # 获取所有数据（分页）
    all_items = []
    page = 1
    max_pages = pagination.get("max_pages", 10)

    while page <= max_pages:
        data = fetch_api_page(endpoint, params, page)
        if not data:
            break
        items = _extract_items_from_response(data, field_mapping)
        if not items:
            break
        all_items.extend(items)
        page += 1

    log(f"  获取到 {len(all_items)} 条数据")

    # 过滤当天数据（按 date_format 决定比较方式）
    today_items = _filter_today_items(all_items, field_mapping, list_config, target_date)
    log(f"  当天 {len(today_items)} 条")

    # 批量入库
    if today_items:
        formatted = [
            {
                "source_name": name,
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "summary": item.get("summary", ""),
                "publish_time": item.get("date", ""),
                "content": "",
                "content_length": 0,
                "batch_id": batch_id,
            }
            for item in today_items
        ]
        from script.db.primary_source import batch_insert
        success_count = batch_insert(formatted, batch_id)
        log(f"  入库 {success_count}/{len(today_items)} 条")
    else:
        success_count = 0

    return {"today": success_count, "total": len(today_items)}


def _extract_items_from_response(data: dict, field_mapping: dict) -> list[dict]:
    """从 API 响应中提取数据列表，并应用字段映射"""
    for path in ["data.list", "data.items", "data.articles", "list", "items", "articles"]:
        items = data
        for key in path.split("."):
            if isinstance(items, dict):
                items = items.get(key, [])
            else:
                items = []
        if items:
            # 应用字段映射
            if field_mapping:
                mapped_items = []
                for item in items:
                    mapped_items.append({
                        "title": item.get(field_mapping.get("title", "title"), ""),
                        "url": item.get(field_mapping.get("url", "url"), ""),
                        "date": item.get(field_mapping.get("date", "date"), ""),
                        "summary": item.get(field_mapping.get("summary", "summary"), ""),
                    })
                return mapped_items
            return items
    if isinstance(data, list):
        return data
    return []


# ==================== 日期注入 + 当天过滤 ====================

# 启发式：扫 params 找值匹配日期形态的 key（兼容旧 config 没存 date_param）
_DATE_VALUE_PATTERNS = [
    (re.compile(r'^\d{8}$'), 'YYYYMMDD'),
    (re.compile(r'^\d{4}-\d{2}-\d{2}$'), 'YYYY-MM-DD'),
    (re.compile(r'^\d{4}/\d{2}/\d{2}$'), 'YYYY/MM/DD'),
    (re.compile(r'^\d{10}$'), 'TIMESTAMP_S'),
    (re.compile(r'^\d{13}$'), 'TIMESTAMP_MS'),
]


def _inject_date_param(params: dict, list_config: dict, target_date: date) -> None:
    """把 params 中的日期值替换为 target_date。

    优先用 list_config 里的 date_param + date_format（学习时已识别）。
    旧 config 没有 date_param 时，扫 params 启发式匹配日期形态的 key 兜底。
    """
    date_param = list_config.get("date_param", "")
    date_format = list_config.get("date_format", "")

    if date_param:
        # 新 config：直接按字段注入
        try:
            params[date_param] = format_date_by_format(target_date, date_format)
        except ValueError:
            log(f"  [WARN] 不支持的 date_format={date_format}，回退到 YYYYMMDD")
            params[date_param] = format_date_by_format(target_date, "YYYYMMDD")
        return

    # 旧 config 兜底：扫 params 找日期形态的 key
    for k, v in list(params.items()):
        if not isinstance(v, str) or not v:
            continue
        for pat, fmt in _DATE_VALUE_PATTERNS:
            if pat.match(v):
                params[k] = format_date_by_format(target_date, fmt)
                break


def _filter_today_items(all_items: list, field_mapping: dict, list_config: dict, target_date: date) -> list:
    """过滤当天的 items（AI新闻支持3天范围）。

    response item 里的日期字段可能是 "2026-06-18 07:04:00" / "20260618" / 时间戳等，
    跟 API param 的 date_format 无关。用 is_within_days 做归一化判断最稳。

    注意：items 已经被 _extract_items_from_response 重映射过，日期固定在 'date' 键上，
    不需要再查 field_mapping（field_mapping 里的 date 字段存的是原始 API 字段名）。
    """
    days = 3 if is_ai_news_db() else 0
    return [
        it for it in all_items
        if is_within_days(str(it.get("date", "")), today_date=target_date, days=days)
    ]