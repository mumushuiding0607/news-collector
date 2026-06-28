"""
analyze_api.py - 分析 API 参数，找日期参数并验证

通用逻辑（不绑定任何特定站点）：
  1. 解析 API URL 已有 query params
  2. 正则扫 param value 找日期形态（YYYYMMDD/YYYY-MM-DD/timestamp/...）
  3. 正则没找到 → 探测：逐个 param 试日期值，看哪个过滤生效
  4. 验证：date_param=today 和 date_param=yesterday 各调一次
     - 都有数据 → 成功
     - 都 0 → 往前推 2/3/5/7 天兜底
     - 都没有 → 抛错

返回：
  {
    "date_param": "bd",
    "date_format": "YYYYMMDD",  # 实际写入时用
    "verified": True,
    "today_items": 50,
    "yesterday_items": 50,
    "params": {k: v},  # 原始 params
  }
"""
import re
from datetime import date, timedelta
from typing import Any
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
import requests

from script.common.datetimeutil import format_date_by_format


# ==================== 日期形态检测 ====================

_DATE_FORMATS = [
    # (regex, format_name, conversion_func)
    (re.compile(r'^(\d{4})(\d{2})(\d{2})$'), 'YYYYMMDD'),
    (re.compile(r'^(\d{4})-(\d{2})-(\d{2})$'), 'YYYY-MM-DD'),
    (re.compile(r'^(\d{4})/(\d{2})/(\d{2})$'), 'YYYY/MM/DD'),
    (re.compile(r'^(\d{10})$'), 'TIMESTAMP_S'),
    (re.compile(r'^(\d{13})$'), 'TIMESTAMP_MS'),
]


def _detect_date_format(value: str) -> str | None:
    """检测一个值是否是日期形态，返回格式名。"""
    if not isinstance(value, str):
        return None
    for pat, name in _DATE_FORMATS:
        if pat.match(value):
            return name
    return None


# ==================== HTTP 工具 ====================

def _build_url(base_url: str, params: dict) -> str:
    """拼 URL（base_url 已含 ? 前缀时直接追加，否则加 ?）。"""
    base_url = base_url.split("?")[0]  # 去掉原 query
    # 过滤掉 jsonp callback 类参数
    params_clean = {k: v for k, v in params.items() if k not in ('cb', 'callback', '_')}
    if not params_clean:
        return base_url
    qs = urlencode(params_clean, doseq=True)
    return f"{base_url}?{qs}"


def _call_api(base_url: str, params: dict, date_param: str | None = None,
              date_value: str | None = None, timeout: int = 10) -> str | None:
    """调一次 API，返回原始响应文本。失败返回 None。"""
    p = dict(params)
    if date_param and date_value is not None:
        p[date_param] = date_value
    # 去掉 jsonp callback
    p.pop('cb', None)
    p.pop('callback', None)
    p.pop('_', None)
    try:
        resp = requests.get(base_url, params=p, timeout=timeout,
                            headers={"User-Agent": "Mozilla/5.0"})
        if resp.status_code != 200:
            return None
        return resp.text
    except Exception:
        return None


def _count_items(text: str) -> int:
    """从响应文本里提取数组项数（找最长的数组）。"""
    import json
    # 剥 jsonp
    m = re.match(r'^\s*\w+\s*\(\s*(.*)\s*\)\s*;?\s*$', text, re.DOTALL)
    if m:
        text = m.group(1)
    try:
        obj = json.loads(text)
    except Exception:
        return 0

    def _walk(node):
        if isinstance(node, list):
            return len(node)
        if isinstance(node, dict):
            best = 0
            for v in node.values():
                best = max(best, _walk(v))
            return best
        return 0
    return _walk(obj)


# ==================== 探测 ====================

def _probe_date_param(base_url: str, params: dict, original_value: str | None = None) -> tuple[str, str] | None:
    """
    探测日期参数：对每个 param 试不同日期格式，看哪个能改变响应。
    返回 (date_param, date_format)，失败返回 None。
    """
    # 用 5 个候选日期：今天 / 2 天前 / 5 天前（差别越大越容易看出来）
    today = date.today()
    candidate_dates = [
        today,
        today - timedelta(days=2),
        today - timedelta(days=5),
    ]

    for param_name in params.keys():
        for fmt in ['YYYYMMDD', 'YYYY-MM-DD', 'YYYY/MM/DD']:
            try:
                sizes = []
                for d in candidate_dates:
                    val = format_date_by_format(d, fmt)
                    text = _call_api(base_url, params, date_param=param_name, date_value=val)
                    if text is None:
                        sizes = []
                        break
                    sizes.append(_count_items(text))
                # 至少一组有数据且大小有差异（说明 param 起作用了）
                if any(s > 0 for s in sizes) and len(set(sizes)) > 1:
                    return (param_name, fmt)
            except Exception:
                continue
    return None


# ==================== 主入口 ====================

class AnalyzeError(Exception):
    """日期参数验证失败。"""
    pass


def analyze_api_params(api_url: str) -> dict:
    """
    分析 API 参数，找日期参数并验证。

    Args:
        api_url: 完整 API URL（含 query string）

    Returns:
        {
            "date_param": "bd",
            "date_format": "YYYYMMDD",
            "verified": True,
            "today_items": 50,
            "yesterday_items": 50,
            "params": {...},  # 原始 params（去掉 cb 等 jsonp 包装）
        }

    Raises:
        AnalyzeError: 找不到日期参数或验证失败
    """
    parsed = urlparse(api_url)
    params = parse_qs(parsed.query)
    # 扁平化
    params_flat = {k: v[0] if len(v) == 1 else v for k, v in params.items()}
    # 去掉 jsonp 包装
    params_clean = {k: v for k, v in params_flat.items() if k not in ('cb', 'callback', '_')}

    base_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"

    # 1. 正则扫已有 param value 找日期形态
    date_param = None
    date_format = None
    for name, value in params_clean.items():
        if isinstance(value, str):
            fmt = _detect_date_format(value)
            if fmt:
                date_param = name
                date_format = fmt
                break
        elif isinstance(value, list):
            for v in value:
                fmt = _detect_date_format(str(v))
                if fmt:
                    date_param = name
                    date_format = fmt
                    break
            if date_param:
                break

    # 2. 正则没找到 → 探测
    if not date_param:
        result = _probe_date_param(base_url, params_clean)
        if result is None:
            raise AnalyzeError("无法识别日期参数")
        date_param, date_format = result

    # 3. 验证：today + yesterday 各调一次
    today = date.today()
    yesterday = today - timedelta(days=1)
    today_val = format_date_by_format(today, date_format)
    yesterday_val = format_date_by_format(yesterday, date_format)
    today_text = _call_api(base_url, params_clean, date_param, today_val)
    yesterday_text = _call_api(base_url, params_clean, date_param, yesterday_val)
    today_count = _count_items(today_text) if today_text else 0
    yesterday_count = _count_items(yesterday_text) if yesterday_text else 0

    if today_count > 0 and yesterday_count > 0:
        return {
            "date_param": date_param,
            "date_format": date_format,
            "verified": True,
            "today_items": today_count,
            "yesterday_items": yesterday_count,
            "params": params_clean,
        }

    # 4. 兜底：往前推 2/3/5/7 天
    for offset in (2, 3, 5, 7):
        past = today - timedelta(days=offset)
        past_val = format_date_by_format(past, date_format)
        past_text = _call_api(base_url, params_clean, date_param, past_val)
        past_count = _count_items(past_text) if past_text else 0
        if past_count > 0:
            return {
                "date_param": date_param,
                "date_format": date_format,
                "verified": True,
                "warning": f"today/yesterday 无数据，最近 {offset} 天前有数据",
                "latest_offset_days": offset,
                "today_items": 0,
                "yesterday_items": 0,
                f"d{offset}_items": past_count,
                "params": params_clean,
            }

    raise AnalyzeError(
        f"日期参数 {date_param} 验证失败：今天和最近 7 天均无数据"
    )
