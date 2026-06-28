"""
find_api.py - 从列表页 HTML 中发现候选 API 端点

通用逻辑（不绑定任何特定站点）：
  1. 正则扫 HTML 找所有 API URL 候选
  2. 黑名单过滤（analytics/track/ads/js lib）
  3. 对每个候选调一次测试请求
  4. 验证 4 条规则（响应必须同时满足才视为"新闻 API"）：
     a) 响应里有数组
     b) 数组项含 URL 字段（值是 http:// 或 /path 形态）
     c) 数组项含时间字段（值匹配日期/时间戳形态）
     d) 数组项含 >10 字中文字段（标题）

返回通过验证的候选列表（按规则匹配度排序）。
"""
import json
import re
from html import unescape
from typing import Any
from urllib.parse import urlparse, parse_qs, urljoin
import requests


# ==================== URL 候选提取 ====================

# 从 HTML 中找 URL 候选：script src, link href, fetch/XHR, ajax, .json/.jsonp 后缀
_API_URL_REGEX = re.compile(
    r'(?:'
    r'<script[^>]+src=["\']([^"\']+)["\']'         # <script src="...">
    r'|'
    r'(?:url|src|href|endpoint|api)["\']?\s*[:=]\s*["\']([^"\']+)["\']'  # url: "..."
    r'|'
    r'(?:fetch|axios|ajax|\$\.get|\$\.ajax)\s*\(\s*["\']([^"\']+)["\']'  # fetch("...")
    r')',
    re.IGNORECASE
)

# 黑名单：明显不是新闻 API 的 host/path 片段
_BLACKLIST_PATTERNS = [
    r'google-analytics\.com',
    r'googletagmanager\.com',
    r'doubleclick\.net',
    r'baidu\.com/(?:hm|tongji|track|ecma)',
    r'/ads?/',
    r'/track(?:ing)?/',
    r'/log(?:s)?/',
    r'/pixel/',
    r'/beacon/',
    r'/stat(?:s|istics)?/',
    r'/monitor/',
    r'/analytics/',
    r'/metrics/',
    r'\.gif(?:\?|$)',
    r'\.png(?:\?|$)',
    r'\.jpg(?:\?|$)',
    r'cdn\.',
    r'static\.',
    r'fonts\.',
    r'css',
    r'\.js(?:\?|$)',
    r'jquery',
    r'react',
    r'vue',
    r'webpack',
]

# API 特征：必须看起来像 API 端点
_API_HINTS = re.compile(
    r'(?:/api/|/v\d+/|/json|/jsonp|list|column|article|news|video|item|feed|query)',
    re.IGNORECASE
)


def _is_blacklisted(url: str) -> bool:
    for pat in _BLACKLIST_PATTERNS:
        if re.search(pat, url, re.IGNORECASE):
            return True
    return False


def _looks_like_api(url: str) -> bool:
    """必须包含 API 特征关键词。例外：.json / .jsonp / 包含 ? 的 URL 可放宽。"""
    if re.search(r'\.(?:json|jsonp)(?:\?|$)', url, re.IGNORECASE):
        return True
    if '?' in url and re.search(r'[&=](?:callback|cb)=', url, re.IGNORECASE):
        return True
    return bool(_API_HINTS.search(url))


def extract_api_candidates(html: str, base_url: str) -> list[str]:
    """
    从 HTML 中提取 API 候选 URL 列表。
    返回去重后的 URL 列表（保留顺序）。
    """
    raw_candidates: list[str] = []
    for m in _API_URL_REGEX.finditer(html):
        # 三组捕获中只有一组会命中
        url = m.group(1) or m.group(2) or m.group(3)
        if not url:
            continue
        url = url.strip()
        # HTML 实体解码（&amp; → &，&quot; → "，&lt; → < 等）
        url = unescape(url)
        # 跳过明显非 URL
        if not url or url.startswith('#') or url.startswith('javascript:'):
            continue
        # 相对路径转绝对
        if url.startswith('//'):
            url = 'http:' + url
        elif url.startswith('/'):
            url = urljoin(base_url, url)
        elif not re.match(r'https?://', url, re.IGNORECASE):
            continue
        raw_candidates.append(url)

    # 去重保留顺序
    seen = set()
    unique = []
    for u in raw_candidates:
        if u not in seen:
            seen.add(u)
            unique.append(u)
    return unique


# ==================== 4 条规则验证 ====================

# URL 字段值形态
_URL_VALUE_REGEX = re.compile(r'^https?://[^\s"\']+|^/[A-Za-z0-9_\-/.]+')

# 时间字段值形态（除了现有 DATETIME_REGEX，再补时间戳）
_TIMESTAMP_REGEX = re.compile(r'^\d{10}$|^\d{13}$')

# 中文字符
_CN_CHAR_REGEX = re.compile(r'[\u4e00-\u9fff]')


def _strip_jsonp(text: str) -> str:
    """去掉 jsonp 包装 cb({...}) → {...}"""
    text = text.strip()
    # 常见 JSONP 形态: callback({...});  cb({...})
    m = re.match(r'^\s*\w+\s*\(\s*(.*)\s*\)\s*;?\s*$', text, re.DOTALL)
    if m:
        return m.group(1)
    return text


def _parse_response(text: str) -> Any:
    """尝试解析 JSON。失败返回 None。"""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        stripped = _strip_jsonp(text)
        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            return None


def _find_arrays(obj: Any, max_depth: int = 5) -> list[list]:
    """递归找响应里的所有数组（按数组长度降序返回）。"""
    arrays: list[list] = []

    def _walk(node, depth):
        if depth > max_depth:
            return
        if isinstance(node, list):
            arrays.append(node)
            # 不递归进入（数组里的元素可能是对象，再走 _walk）
            for item in node:
                _walk(item, depth + 1)
        elif isinstance(node, dict):
            for v in node.values():
                _walk(v, depth + 1)

    _walk(obj, 0)
    # 按长度降序：最长的数组最可能是新闻列表
    arrays.sort(key=len, reverse=True)
    return arrays


def _validate_array(items: list) -> dict:
    """
    对数组前 N 项做 4 条规则验证。
    返回 {ok, url_field, time_field, title_field, summary_field, score}。
    """
    if not items or not isinstance(items[0], dict):
        return {"ok": False, "reason": "数组项不是 dict"}

    sample_size = min(5, len(items))
    samples = items[:sample_size]

    # 收集每个字段在 sample 中匹配各规则的比例
    field_url_hits: dict[str, int] = {}
    field_time_hits: dict[str, int] = {}
    field_cn_hits: dict[str, int] = {}
    field_cn_char_counts: dict[str, list[int]] = {}

    for item in samples:
        for k, v in item.items():
            if not isinstance(v, str):
                continue
            # URL 规则
            if _URL_VALUE_REGEX.match(v):
                field_url_hits[k] = field_url_hits.get(k, 0) + 1
            # 时间规则
            from script.common.datetimeutil import DATETIME_REGEX
            if DATETIME_REGEX.search(v) or _TIMESTAMP_REGEX.match(v):
                field_time_hits[k] = field_time_hits.get(k, 0) + 1
            # 中文字数
            cn_count = len(_CN_CHAR_REGEX.findall(v))
            if cn_count > 0:
                field_cn_hits[k] = field_cn_hits.get(k, 0) + 1
                field_cn_char_counts.setdefault(k, []).append(cn_count)

    # URL 字段：>50% 命中，且优先选"不同时匹配时间"的（避免把 image 路径误判）
    url_only = {k: v for k, v in field_url_hits.items() if k not in field_time_hits}
    url_field = _majority_field(url_only if url_only else field_url_hits, sample_size)
    # 时间字段：>50% 命中，且优先选"不同时匹配 URL"的（避免把 image 路径误判）
    time_only = {k: v for k, v in field_time_hits.items() if k not in field_url_hits}
    time_field = _majority_field(time_only if time_only else field_time_hits, sample_size)
    # 进一步优化：含 4 位年份的优先（time="2026-06-18 07:04:00" 比 length="00:53:35" 更好）
    if time_field and field_time_hits and len(time_only) > 1:
        year_fields = []
        for fname in time_only:
            for item in samples[:1]:
                v = item.get(fname, "")
                if isinstance(v, str) and re.search(r'\b20\d{2}\b', v):
                    year_fields.append(fname)
                    break
        if year_fields and time_field not in year_fields:
            time_field = year_fields[0]
    # 进一步优化 URL 字段：优先选"看起来像文章链接"的（以 .shtml/.html/.htm 结尾）
    if url_field and field_url_hits:
        article_ext_fields = []
        for fname, hits in field_url_hits.items():
            if hits < max(1, int(sample_size * 0.6)):
                continue
            # 取样一个 item 看值
            for item in samples[:1]:
                v = item.get(fname, "")
                if isinstance(v, str) and re.search(r'\.(shtml|html|htm)(?:\?|$)', v, re.IGNORECASE):
                    article_ext_fields.append(fname)
                    break
        if article_ext_fields and url_field not in article_ext_fields:
            url_field = article_ext_fields[0]
    # 标题字段：>50% 命中 且 中文 > 10
    title_candidates = {k for k, c in field_cn_hits.items()
                        if c > sample_size / 2
                        and any(n > 10 for n in field_cn_char_counts.get(k, []))}
    # 摘要字段：中文最多的那个
    summary_candidates = {k for k, counts in field_cn_char_counts.items()
                          if any(n > 10 for n in counts)}

    if not title_candidates:
        return {"ok": False, "reason": "找不到标题字段（中文 > 10 字段）"}

    if not url_field:
        return {"ok": False, "reason": "找不到 URL 字段"}

    if not time_field:
        return {"ok": False, "reason": "找不到时间字段"}

    return {
        "ok": True,
        "url_field": url_field,
        "time_field": time_field,
        "title_fields": sorted(title_candidates),
        "summary_fields": sorted(summary_candidates),
    }


def _majority_field(hits: dict[str, int], total: int) -> str | None:
    """取命中数最多的字段（>50% 才算）。"""
    if not hits:
        return None
    best = max(hits.items(), key=lambda x: x[1])
    if best[1] > total / 2:
        return best[0]
    return None


# ==================== 主入口 ====================

def find_api(html: str, base_url: str, headline: str = "", test_timeout: int = 10) -> list[dict]:
    """
    从 HTML 找 API 候选，验证后返回通过验证的候选列表。

    Args:
        html: 列表页原始 HTML
        base_url: 列表页 URL（用于相对路径转绝对）
        headline: 已知文章标题（用于多候选消歧）
        test_timeout: 单个 API 测试请求超时（秒）

    Returns:
        通过验证的候选列表，每项：
          {
            "url": "https://api.example.com/...",
            "method": "GET",
            "params": {...},  # 从 URL query 解析
            "sample_count": N,
            "url_field": "url",
            "time_field": "time",
            "title_fields": [...],
            "summary_fields": [...],
          }
        没有通过验证的返回空列表。
    """
    candidates = extract_api_candidates(html, base_url)
    # 过滤黑名单
    candidates = [u for u in candidates if not _is_blacklisted(u) and _looks_like_api(u)]
    if not candidates:
        return []

    validated: list[dict] = []
    for url in candidates:
        try:
            result = _test_candidate(url, test_timeout)
        except Exception:
            continue
        if result is None:
            continue
        url_field = result.get("url_field")
        time_field = result.get("time_field")
        title_fields = result.get("title_fields", [])
        if not (url_field and time_field and title_fields):
            continue
        # 解析 query params
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        # 扁平化
        params_flat = {k: v[0] if len(v) == 1 else v for k, v in params.items()}
        validated.append({
            "url": url.split("?")[0],  # 去掉 query，参数走 params
            "method": "GET",
            "params": params_flat,
            "sample_count": result["sample_count"],
            "url_field": url_field,
            "time_field": time_field,
            "title_fields": title_fields,
            "summary_fields": result.get("summary_fields", []),
        })

    if not validated:
        return []

    # 消歧：有 headline 时优先用 headline 命中的
    if headline and len(validated) > 1:
        for v in validated:
            try:
                resp = requests.get(v["url"], params=v["params"], timeout=test_timeout)
                text = resp.text
                if headline in text:
                    return [v]
            except Exception:
                continue
    # 默认按 sample_count 降序
    validated.sort(key=lambda x: x["sample_count"], reverse=True)
    return validated


def _test_candidate(url: str, timeout: int) -> dict | None:
    """对单个候选发测试请求，验证 4 条规则。

    为应对"原 URL 锁死特定日期导致当天 0 条"的情况，会尝试：
      1. 原 URL 直接调
      2. 去掉所有日期形态的 query param
      3. 把日期形态的 param 设成今天/昨天
    任一调用拿到 ≥3 项且通过验证即算成功。
    """
    from datetime import date, timedelta
    from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

    parsed = urlparse(url)
    base = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    raw_params = parse_qs(parsed.query)
    # 识别日期形态的 param
    date_params: dict[str, str] = {}  # param_name -> detected_format
    for name, values in raw_params.items():
        for v in values:
            for pat, fmt in [(re.compile(r'^\d{8}$'), 'YYYYMMDD'),
                             (re.compile(r'^\d{4}-\d{2}-\d{2}$'), 'YYYY-MM-DD'),
                             (re.compile(r'^\d{4}/\d{2}/\d{2}$'), 'YYYY/MM/DD')]:
                if pat.match(v):
                    date_params[name] = fmt
                    break

    # 多组调用尝试
    today = date.today()
    yesterday = today - timedelta(days=1)
    call_attempts: list[dict] = []

    # 1. 原 URL
    call_attempts.append(dict(raw_params))

    # 2. 去掉日期 param
    if date_params:
        no_date = {k: v for k, v in raw_params.items() if k not in date_params}
        call_attempts.append(no_date)

    # 3. 日期 param 设今天/昨天
    for dp_name, dp_fmt in date_params.items():
        for d in (today, yesterday):
            new_params = {k: v for k, v in raw_params.items() if k != dp_name}
            if dp_fmt == 'YYYYMMDD':
                new_params[dp_name] = [d.strftime('%Y%m%d')]
            elif dp_fmt == 'YYYY-MM-DD':
                new_params[dp_name] = [d.strftime('%Y-%m-%d')]
            elif dp_fmt == 'YYYY/MM/DD':
                new_params[dp_name] = [d.strftime('%Y/%m/%d')]
            call_attempts.append(new_params)

    for params in call_attempts:
        # 去掉 jsonp 包装
        clean = {k: v for k, v in params.items() if k not in ('cb', 'callback', '_')}
        # 扁平化
        flat = {k: v[0] if len(v) == 1 else v for k, v in clean.items()}
        try:
            resp = requests.get(base, params=flat, timeout=timeout,
                                headers={"User-Agent": "Mozilla/5.0"})
        except Exception:
            continue
        if resp.status_code != 200:
            continue
        obj = _parse_response(resp.text)
        if obj is None:
            continue
        arrays = _find_arrays(obj)
        for arr in arrays:
            if len(arr) < 3:
                continue
            result = _validate_array(arr)
            if result.get("ok"):
                result["sample_count"] = len(arr)
                return result
    return None
