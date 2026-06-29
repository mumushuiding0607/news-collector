"""
list_discovery.py - 新闻列表配置发现

使用 LLM 分析新闻网站，输出可存入 source_crawl_configs 的配置。

统一学习入口 learn_source_config 见 learn_source.py。
"""
import asyncio
from pathlib import Path

from script.bootstrap import *
from script.llm.client import call as llm_call
from script.llm.client import call_async_raw, parse_response
from script.log import log as _log
from script.discovery.html_cleaner import clean_html
from script.discovery.util.html_text_sanitizer import sanitize_html_for_llm
from script.discovery.util.news_block_truncator import truncate_html_by_news_items

# Maximum HTML size to send to LLM (50KB)
MAX_HTML_SIZE = 50 * 1024


def log(msg: str):
    _log("list_discovery", msg)


PROMPT_PATH = Path(__file__).parent.parent.parent / "prompt" / "新闻列表发现.md"
PROMPT_TEMPLATE = PROMPT_PATH.read_text(encoding="utf-8")


def discover_list_config(url: str, html: str, use_raw_fallback: bool = True, headline: str = "", already_cleaned: bool = False, force_relearn: bool = False) -> dict:
    """
    发现新闻列表配置。

    策略：
    1. 清洗 HTML（already_cleaned=True 时跳过）
    2. 按新闻块截取 HTML（确保每个新闻块完整）
    3. LLM DOM 分析（headline 用于多候选列表时的消歧）
    4. raw_fetch 兜底（embedded JSON）

    Args:
        url: 列表页 URL
        html: HTML 内容（原始或已清洗，取决于 already_cleaned）
        use_raw_fallback: LLM 失败时是否尝试 raw_fetch 兜底
        headline: 已知文章标题（用于多候选列表块消歧）
        already_cleaned: html 是否已经过 clean_html 处理。
                        True 跳过内部 clean_html（避免双重 clean 把 HTML 压到几乎为空）。

    Returns:
        可存入 source_crawl_configs 的配置字典
    """
    if already_cleaned:
        cleaned_str = html
        log("[Step 1] 跳过 clean_html（输入已清洗）")
        # 已清洗的 HTML 可能已不含 <script>（clean_html 删掉了）。
        # 检测 __NEXT_DATA__ 需要原始 HTML，尝试 raw_fetch 补获。
        if "__NEXT_DATA__" not in html and not force_relearn:
            from script.discovery.raw_fetch import fetch_raw_html
            raw = fetch_raw_html(url)
            if raw and "__NEXT_DATA__" in raw:
                log("[Step 1] 检测到 __NEXT_DATA__（raw_fetch 补获），直接走 embedded JSON 路径")
                return _discover_with_raw_fetch(url)
    else:
        # __NEXT_DATA__ 嵌入式 JSON 站点（Next.js）：clean_html 会删掉 <script> 标签，
        # 导致 HTML 变空。优先在 clean 之前检测并走 raw_fetch 路径。
        # 但 force_relearn=True 时跳过此快捷路径，强制走 HTML+LLM 分析。
        if "__NEXT_DATA__" in html and not force_relearn:
            log("[Step 1] 检测到 __NEXT_DATA__，跳过 LLM HTML 分析，直接用 embedded JSON")
            return _discover_with_raw_fetch(url)
        cleaned = clean_html(html)
        cleaned_str = cleaned.html
        log(f"[Step 1] HTML 清洗完成，移除 {cleaned.removed_count} 个标签")

    log("[Step 1.2] 开始 LLM DOM 分析...")
    truncated_html = truncate_html_by_news_items(cleaned_str, MAX_HTML_SIZE)
    log(f"[Step 1.2] HTML 截取后长度: {len(truncated_html)}")

    # 脱敏文本后再送 LLM：保留 DOM 结构，替换用户文本为占位符，
    # 避免上游 API 因敏感词直接拒答（HTTP 500 "output new_sensitive"）
    sanitized_html = sanitize_html_for_llm(truncated_html)
    log(f"[Step 1.2] HTML 脱敏后长度: {len(sanitized_html)}")

    headline_hint = (
        f"\n\n## 参考：已知文章标题\n以下标题属于目标新闻列表，请据此确认哪个列表块是正确的：\n{headline}\n"
        if headline else ""
    )
    user_msg = f"url: {url}{headline_hint}\n\nhtml: {sanitized_html}"

    try:
        # max_tokens=None：不限制 → LLM 不会截断 → 不需要翻倍重试。
        # 历史曾用 16000 + auto_grow_on_truncate，但 Stage 2 已删，参数也作废。
        full_prompt = PROMPT_TEMPLATE + "\n\n" + user_msg
        blocks = asyncio.run(call_async_raw(full_prompt, timeout=180))
        response = parse_response(blocks) if blocks else None
        if response is not None:
            log(f"[Step 1.2] LLM 分析成功: {response.get('name', 'unknown')} ({response.get('source_type', 'unknown')})")
            return response
        log("[Step 1.2] LLM 调用返回 None")
    except Exception as e:
        log(f"[Step 1.2] LLM 调用失败: {e}")

    if use_raw_fallback:
        log("[Step 2] Step 1.2失败，开始 Step 2 raw_fetch 兜底...")
        return _discover_with_raw_fetch(url)

    return {}


def _discover_with_raw_fetch(url: str) -> dict:
    """
    Step 2: raw_fetch 兜底。embedded JSON 检测。

    Returns:
        配置字典
    """
    from script.discovery.raw_fetch import fetch_raw_html
    from script.discovery.util.json_extractor import find_embedded_json

    raw_html = fetch_raw_html(url)
    if not raw_html:
        log("[raw fetch] 无法获取原始 HTML")
        return {}
    log(f"[raw fetch] 获取成功，HTML长度={len(raw_html)}")

    log("[Step 2.1] embedded JSON 检测...")
    json_data = find_embedded_json(raw_html)
    if json_data:
        # __NEXT_DATA__ 结构（Next.js）：硬编码字段映射，不需要 LLM
        if isinstance(json_data, dict) and "pageProps" in json_data:
            log("[Step 2.1] 检测到 __NEXT_DATA__（Next.js），使用固定字段映射")
            return {
                "name": "原始HTTP(JSON)",
                "source_type": "raw",
                "list_config": {
                    "type": "raw",
                    "list_complete": True,
                    "url_field": "shareInfo.shareUrl",
                    "title_field": "title",
                    "time_field": "time",
                    "summary_field": "text",
                    "date_format": "__next_data__",
                    "is_next_data": True,
                },
            }

        log("[Step 2.1] 检测到嵌入式 JSON，尝试 LLM 字段映射")
        field_mapping = _analyze_json_fields(json_data, url)
        if field_mapping:
            return {
                "name": "原始HTTP(JSON)",
                "source_type": "raw",
                "list_config": {
                    "type": "raw",
                    "list_complete": True,
                    "url_field": field_mapping.get("url_field", "url"),
                    "title_field": field_mapping.get("title_field", "title"),
                    "time_field": field_mapping.get("time_field", "createTime"),
                    "summary_field": field_mapping.get("summary_field", "summary"),
                    "date_format": field_mapping.get("date_format", "unix"),
                },
            }
        log("[Step 2.1] LLM 字段映射失败")

    log("[Step 2] 所有方法失败")
    return {}


def _navigate_next_data(data: dict) -> list:
    """
    从 __NEXT_DATA__（Next.js）嵌入式 JSON 中提取 innermost 新闻列表。

    典型路径：pageProps.pageProps.initSsrData.pageInfo.list[].timeList[]
    返回 timeList[] 条目组成的列表（每条含 title、url、text、time、dateInfo）。
    """
    page_props = data.get("pageProps", {})
    if isinstance(page_props, dict):
        inner = page_props.get("pageProps", {})
        if isinstance(inner, dict):
            ssr = inner.get("initSsrData", {})
        else:
            ssr = inner if isinstance(inner, list) else {}
    else:
        ssr = {}

    page_info = ssr.get("pageInfo", {})
    news_list = page_info.get("list", [])

    result = []
    for day_group in news_list:
        if not isinstance(day_group, dict):
            continue
        time_list = day_group.get("timeList", [])
        for item in time_list:
            if not isinstance(item, dict):
                continue
            # 合成完整 datetime
            date_info = item.get("dateInfo", {}) or {}
            year = date_info.get("year", "")
            month = date_info.get("month", "")
            day = date_info.get("day", "")
            time_str = item.get("time", "")
            if year and month and day:
                full_date = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                full_datetime = f"{full_date} {time_str}:00" if time_str else f"{full_date} 00:00:00"
            else:
                full_datetime = time_str

            # 处理 URL
            url = item.get("url", "")
            if not url:
                share_info = item.get("shareInfo", {}) or {}
                url = share_info.get("shareUrl", "")
            if url and not url.startswith("http"):
                url = "https://www.cnstock.com" + url

            result.append({
                "title": item.get("title", "") or item.get("name", ""),
                "url": url,
                "text": item.get("text", ""),
                "time": full_datetime,
                "dateInfo": date_info,
            })
    return result


def _analyze_json_fields(json_data: dict | list, url: str) -> dict:
    """
    使用 LLM 分析嵌入式 JSON 结构，确定字段映射。

    若是 __NEXT_DATA__ 结构（Next.js），先导航到 innermost 新闻列表再分析。
    """
    # 处理 __NEXT_DATA__ 嵌套结构：pageProps.pageProps.initSsrData.pageInfo.list[].timeList[]
    if isinstance(json_data, dict) and "pageProps" in json_data:
        json_data = _navigate_next_data(json_data)
    """
    使用 LLM 分析嵌入式 JSON 结构，确定字段映射。

    Returns:
        字段映射 dict
    """
    if isinstance(json_data, list):
        samples = json_data[:3]
    elif isinstance(json_data, dict):
        samples = [json_data]
    else:
        return {}

    if not samples:
        return {}

    sample_str = json.dumps(samples[0], ensure_ascii=False, indent=2)
    if len(sample_str) > 2000:
        sample_str = sample_str[:2000] + "..."

    prompt = f"""分析以下嵌入式 JSON，判断它是否是新闻列表，并确定字段映射。

URL: {url}

JSON 样本（第一条记录）:
{sample_str}

请返回 JSON 格式，包含以下信息：
1. is_news_list: 是否是新闻列表（true/false）
2. url_field: 文章链接字段名
3. title_field: 文章标题字段名
4. time_field: 发布时间字段名
5. summary_field: 文章摘要字段名

只返回 JSON，不要解释。"""

    try:
        # 500：JSON 字段映射输出极简（5 字段 + true/false），500 tokens 足够
        response = llm_call(prompt)
        if response is None or not isinstance(response, dict):
            return {}

        if not response.get("is_news_list", False):
            return {}

        field_mapping = {
            "url_field": response.get("url_field", "url"),
            "title_field": response.get("title_field", "title"),
            "time_field": response.get("time_field", "createTime"),
            "summary_field": response.get("summary_field", "summary"),
        }

        # 推断日期格式
        time_field = field_mapping["time_field"]
        sample_values = []
        if isinstance(json_data, list):
            for item in json_data[:10]:
                v = item.get(time_field)
                if v is not None:
                    sample_values.append(v)
        elif isinstance(json_data, dict):
            v = json_data.get(time_field)
            if v is not None:
                sample_values.append(v)

        if sample_values:
            from script.common.datetime_parser import learn_date_format
            field_mapping["date_format"] = learn_date_format(sample_values)

        return field_mapping
    except Exception as e:
        log(f"[raw fetch] LLM 分析 JSON 失败: {e}")
        return {}