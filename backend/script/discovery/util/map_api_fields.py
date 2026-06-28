"""
map_api_fields.py - 取 API 样本 + 字段映射（值识别优先，LLM 补缺）

两阶段：
  1. fetch_api_sample：调 API 拿样本（date=today），客户端兜底过滤当天
  2. discover_api_field_mapping：
     ① 值识别（URL/中文>10/中文最多/时间）— 用值而非名称判断
     ② 缺哪个字段 → LLM 补（内联 prompt，3 条样本，字符串截断）
     ③ 输出统一 list_dom_result 格式（source_type=api）
"""
import json
import re
from datetime import date, datetime, timedelta
from typing import Any
from urllib.parse import urlencode
import requests

from script.common.datetimeutil import DATETIME_REGEX, is_today, today_iso, format_date_by_format
from script.llm.client import call as llm_call


# ==================== fetch_api_sample ====================

def fetch_api_sample(base_url: str, analysis: dict, timeout: int = 15) -> dict:
    """
    调一次 API 拿样本（date=today），客户端兜底过滤当天新闻。

    Args:
        base_url: API 基础 URL（不含 query）
        analysis: analyze_api_params 的输出

    Returns:
        {
            "items": [...],         # 过滤后的当天项
            "raw_count": N,         # 过滤前总数
            "today_count": N,       # 过滤后天数
        }
    """
    today = date.today()
    # 把 date_format 转换为对应字符串
    fmt = analysis['date_format']
    today_val = format_date_by_format(today, fmt)

    params = dict(analysis['params'])
    params[analysis['date_param']] = today_val

    resp = requests.get(base_url, params=params, timeout=timeout,
                        headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    items = _extract_array(resp.text)
    raw_count = len(items)

    # 客户端兜底：扫描每个 item，找含今天日期形态的字段，保留
    today_strs = _today_string_variants(today)
    today_strs.append(fmt)  # 也匹配 raw timestamp 等
    today_items = []
    for item in items:
        if not isinstance(item, dict):
            continue
        if _item_matches_today(item, today_strs):
            today_items.append(item)

    return {
        "items": today_items,
        "raw_count": raw_count,
        "today_count": len(today_items),
    }


def _today_string_variants(d: date) -> list[str]:
    """生成今天日期的所有常见字符串形态。"""
    return [
        d.strftime('%Y%m%d'),
        d.strftime('%Y-%m-%d'),
        d.strftime('%Y/%m/%d'),
        d.strftime('%Y.%m.%d'),
        f"{d.year}年{d.month}月{d.day}日",
    ]


def _item_matches_today(item: dict, today_strs: list[str]) -> bool:
    """item 的某个字段值是否包含今天日期形态。"""
    for v in item.values():
        if not isinstance(v, str):
            continue
        for ts in today_strs:
            if ts in v:
                return True
    return False


def _strip_jsonp(text: str) -> str:
    text = text.strip()
    m = re.match(r'^\s*\w+\s*\(\s*(.*)\s*\)\s*;?\s*$', text, re.DOTALL)
    if m:
        return m.group(1)
    return text


def _extract_array(text: str) -> list:
    """从响应文本里找最长的数组。"""
    stripped = _strip_jsonp(text)
    try:
        obj = json.loads(stripped)
    except Exception:
        return []

    best: list = []

    def _walk(node):
        nonlocal best
        if isinstance(node, list):
            if len(node) > len(best):
                best = node
            for item in node:
                _walk(item)
        elif isinstance(node, dict):
            for v in node.values():
                _walk(v)

    _walk(obj)
    return best


# ==================== discover_api_field_mapping ====================

_URL_VALUE_REGEX = re.compile(r'^https?://[^\s"\']+|^/[A-Za-z0-9_\-/.]+')
_TIMESTAMP_REGEX = re.compile(r'^\d{10}$|^\d{13}$')
_CN_CHAR_REGEX = re.compile(r'[\u4e00-\u9fff]')

# LLM 补缺的内联 prompt（精炼）
_LLM_PROMPT_TEMPLATE = """API 响应（截断 3 条，字符串已截 200 字符）:
{items_json}

请指出 url/title/time/summary 字段名。JSON 输出:
{{"url":"...","title":"...","time":"...","summary":"..."}}
无则填空串。"""


def discover_api_field_mapping(items: list[dict], api_url: str, name: str = "",
                                analysis: dict | None = None) -> dict:
    """
    字段映射：值识别优先，LLM 补缺。

    Args:
        items: API 响应数组（前 N 条即可）
        api_url: API URL
        name: 数据源名称
        analysis: analyze_api_params 的输出（可选，用于补全 api section）

    Returns:
        list_dom_result 格式（source_type=api）：
        {
            "name": "...",
            "source_type": "api",
            "publish_time_pattern": "",
            "article": {"url": ..., "title": ..., "publish_time": ...},
            "api": {"url": ..., "method": "GET", "params": ...},
            "field_mapping": {"url": ..., "title": ..., "publish_time": ..., "summary": ...}
        }
    """
    if not items:
        raise ValueError("items 为空，无法做字段映射")

    sample_size = min(5, len(items))
    samples = [it for it in items[:sample_size] if isinstance(it, dict)]
    if not samples:
        raise ValueError("items 中没有 dict 类型")

    # === Stage 1: 值识别 ===
    url_field, time_field, title_field, summary_field = _detect_by_value(samples)

    # === Stage 2: LLM 补缺 ===
    missing = []
    if not url_field:
        missing.append("url")
    if not time_field:
        missing.append("time")
    if not title_field:
        missing.append("title")
    if not summary_field:
        missing.append("summary")

    llm_mapping: dict = {}
    if missing:
        llm_mapping = _llm_complete_fields(samples, missing)

    if not url_field:
        url_field = llm_mapping.get("url", "")
    if not time_field:
        time_field = llm_mapping.get("time", "")
    if not title_field:
        title_field = llm_mapping.get("title", "")
    if not summary_field:
        summary_field = llm_mapping.get("summary", "")

    if not (url_field and title_field):
        raise ValueError(f"关键字段未识别: url={url_field}, title={title_field}")

    # === 组装 list_dom_result 格式 ===
    # 取第一条作为 article 样本
    first = samples[0]
    article = {
        "url": str(first.get(url_field, "")),
        "title": str(first.get(title_field, "")),
        "publish_time": _normalize_publish_time(first.get(time_field, "")) if time_field else "",
    }

    api_section: dict = {
        "url": api_url,
        "method": "GET",
    }
    if analysis:
        api_section["params"] = analysis.get("params", {})
        api_section["date_param"] = analysis.get("date_param", "")
        api_section["date_format"] = analysis.get("date_format", "")

    return {
        "name": name,
        "source_type": "api",
        "publish_time_pattern": "",
        "article": article,
        "api": api_section,
        "field_mapping": {
            "url": url_field,
            "title": title_field,
            "publish_time": time_field,
            "summary": summary_field,
        },
    }


def _detect_by_value(samples: list[dict]) -> tuple[str | None, str | None, str | None, str | None]:
    """
    通过值识别字段。返回 (url_field, time_field, title_field, summary_field)。

    - URL 字段：值匹配 URL 形态（http:// 或 /path），跨样本 >60% 一致
    - 时间字段：值匹配 DATETIME_REGEX 或时间戳
    - 标题字段：值含 >10 个中文字（且不是"最长的那个"）
    - 摘要字段：值含中文字数最多的那个
    """
    if not samples:
        return None, None, None, None

    n = len(samples)
    # 收集每个字段的"特征命中次数"
    url_hits: dict[str, int] = {}
    time_hits: dict[str, int] = {}
    cn_hits: dict[str, int] = {}
    cn_char_counts: dict[str, list[int]] = {}

    for item in samples:
        for k, v in item.items():
            if not isinstance(v, str):
                continue
            # URL 规则
            if _URL_VALUE_REGEX.match(v):
                url_hits[k] = url_hits.get(k, 0) + 1
            # 时间规则
            if DATETIME_REGEX.search(v) or _TIMESTAMP_REGEX.match(v):
                time_hits[k] = time_hits.get(k, 0) + 1
            # 中文字数
            cn = len(_CN_CHAR_REGEX.findall(v))
            if cn > 0:
                cn_hits[k] = cn_hits.get(k, 0) + 1
                cn_char_counts.setdefault(k, []).append(cn)

    # URL 字段：>60% 命中，优先"不同时匹配时间"（排除 image 类含日期路径的字段）
    url_only = {k: v for k, v in url_hits.items() if k not in time_hits}
    url_field = None
    pool = url_only if url_only else url_hits
    if pool:
        best = max(pool.items(), key=lambda x: x[1])
        if best[1] >= max(1, int(n * 0.6)):
            url_field = best[0]
    # URL 字段再优化：值以 .shtml/.html/.htm 结尾的优先
    if url_field and url_hits:
        article_ext_fields = []
        for fname, hits in url_hits.items():
            if hits < max(1, int(n * 0.6)):
                continue
            for item in samples[:1]:
                v = item.get(fname, "")
                if isinstance(v, str) and re.search(r'\.(shtml|html|htm)(?:\?|$)', v, re.IGNORECASE):
                    article_ext_fields.append(fname)
                    break
        if article_ext_fields and url_field not in article_ext_fields:
            url_field = article_ext_fields[0]

    # 时间字段：>60% 命中，优先"不同时匹配 URL"
    time_only = {k: v for k, v in time_hits.items() if k not in url_hits}
    time_field = None
    pool = time_only if time_only else time_hits
    if pool:
        best = max(pool.items(), key=lambda x: x[1])
        if best[1] >= max(1, int(n * 0.6)):
            time_field = best[0]
    # 时间字段再优化：含 4 位年份的优先（"2026-06-18 ..." 比 "00:53:35" 更好）
    if time_field and time_only and len(time_only) > 1:
        year_fields = []
        for fname in time_only:
            for item in samples[:1]:
                v = item.get(fname, "")
                if isinstance(v, str) and re.search(r'\b20\d{2}\b', v):
                    year_fields.append(fname)
                    break
        if year_fields and time_field not in year_fields:
            time_field = year_fields[0]

    # 中文候选字段：必须有样本含 >10 中文
    title_candidates = {k for k, c in cn_hits.items()
                        if c >= max(1, int(n * 0.6))
                        and any(num > 10 for num in cn_char_counts.get(k, []))}
    # 排除"摘要"（中文字数最多的）
    summary_field = None
    if cn_char_counts:
        # 找平均字数最多的字段
        avg_counts = {k: sum(nums) / len(nums) for k, nums in cn_char_counts.items()
                      if any(n > 10 for n in nums)}
        if avg_counts:
            summary_field = max(avg_counts.items(), key=lambda x: x[1])[0]

    # 标题字段：在 title_candidates 里排除 summary 字段
    title_field = None
    title_pool = title_candidates - {summary_field} if summary_field else title_candidates
    if title_pool:
        # 选平均字数较少（短一些）的当标题
        avg_in_pool = {k: sum(cn_char_counts[k]) / len(cn_char_counts[k]) for k in title_pool}
        title_field = min(avg_in_pool.items(), key=lambda x: x[1])[0]

    return url_field, time_field, title_field, summary_field


def _llm_complete_fields(samples: list[dict], missing: list[str]) -> dict:
    """LLM 补缺：传 3 条样本（字符串截断），输出缺失字段名。"""
    # 截断：3 条 + 字符串 200 字符
    truncated = []
    for item in samples[:3]:
        new_item = {}
        for k, v in item.items():
            if isinstance(v, str):
                k_trunc = k[:30]
                v_trunc = v[:200]
                new_item[k_trunc] = v_trunc
            else:
                new_item[k[:30]] = v
        truncated.append(new_item)
    items_json = json.dumps(truncated, ensure_ascii=False, indent=1)
    prompt = _LLM_PROMPT_TEMPLATE.format(items_json=items_json)

    try:
        resp = llm_call(prompt)
        # resp 是 dict | None
        if isinstance(resp, dict):
            # 只取缺失的字段
            return {k: resp.get(k, "") for k in missing}
    except Exception:
        pass
    return {k: "" for k in missing}


def _normalize_publish_time(value: Any) -> str:
    """把各种时间形态规范化为 YYYY-MM-DD HH:MM:SS。"""
    if not value:
        return ""
    if isinstance(value, int):
        # 时间戳
        try:
            if value > 1e12:
                dt = datetime.fromtimestamp(value / 1000)
            else:
                dt = datetime.fromtimestamp(value)
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        except Exception:
            return str(value)
    s = str(value)
    # 试 13/10 位数字字符串
    if s.isdigit() and len(s) in (10, 13):
        try:
            ts = int(s)
            if len(s) == 13:
                ts = ts / 1000
            return datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
        except Exception:
            pass
    # 用 parse_publish_time 规范化
    from script.common.datetimeutil import parse_publish_time
    normalized = parse_publish_time(s)
    return normalized or s
