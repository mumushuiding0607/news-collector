"""
content_discovery.py - 新闻正文配置发现

使用 LLM 分析新闻文章页，输出可存入 source_crawl_configs 的配置。
"""
import asyncio
from pathlib import Path

from script.bootstrap import *
from script.llm.client import call as llm_call
from script.llm.client import call_async_raw, parse_response
from script.log import log as _log
from script.discovery.util.html_text_sanitizer import sanitize_html_for_llm
from script.discovery.util.html_truncate import safe_truncate
from script.discovery.util.learning_log import save_learning_html

# Maximum HTML size to send to LLM (50KB)
MAX_HTML_SIZE = 50 * 1024


def log(msg: str):
    _log("content_discovery", msg)


PROMPT_PATH = Path(__file__).parent.parent.parent / "prompt" / "新闻正文发现.md"
PROMPT_TEMPLATE = PROMPT_PATH.read_text(encoding="utf-8")


def discover_content_config(url: str, html: str, headline: str = "") -> dict:
    """
    使用 LLM 分析新闻文章页，返回配置。

    Args:
        url: 新闻文章页 URL
        html: 网页 HTML 内容
        headline: 文章标题（可选，用于帮助 LLM 定位内容）

    Returns:
        可存入 source_crawl_configs 的配置字典
    """
    from script.discovery.html_cleaner import clean_article_html

    # 清洗 HTML：移除无用标签、保留 DOM 结构（用于选择器定位）
    cleaned_html = clean_article_html(html)
    save_learning_html(url, cleaned_html, "article_cleaned", log)

    # 截断到 50KB（在最近的完整标签处安全切断）
    truncated_html = safe_truncate(cleaned_html, MAX_HTML_SIZE)

    # 脱敏文本后再送 LLM：保留 DOM 结构，替换用户文本为占位符，
    # 避免上游 API 因敏感词直接拒答（HTTP 500 "output new_sensitive"）
    sanitized_html = sanitize_html_for_llm(truncated_html)
    log(f"HTML 脱敏后长度: {len(sanitized_html)}")

    # 如果有 headline，添加到上下文帮助 LLM 定位
    headline_hint = (
        f"\n\n已知文章标题: {headline}\n请根据标题确认这是哪篇报道。" if headline else ""
    )
    user_msg = f"""url: {url}
{headline_hint}

html: {sanitized_html}"""

    try:
        # max_tokens=None：不限制 → LLM 不会截断 → 不需要翻倍重试。
        # 历史曾用 16000 + auto_grow_on_truncate，但 Stage 2 已删，参数也作废。
        full_prompt = PROMPT_TEMPLATE + "\n\n" + user_msg
        blocks = asyncio.run(call_async_raw(full_prompt, timeout=180))
        response = parse_response(blocks) if blocks else None
        if response is None:
            log("LLM 调用返回 None")
            return {}

        ce = response.get("content_extract", {})
        pt = response.get("publish_time_pattern") or ""
        ts = ce.get("time_selector", "") if ce else ""

        log(f"文章URL: {url}")
        if headline:
            log(f"文章标题: {headline}")
        log(f"正文配置: selector={ce.get('selector', 'unknown')}")

        _log_time_extraction(html, ts, pt)
        return response
    except Exception as e:
        log(f"LLM 调用失败: {e}")
        return {}


def _log_time_extraction(html: str, time_selector: str, pattern: str) -> None:
    """如果发现时间配置，尝试提取实际发布时间并记录日志"""
    if not (time_selector or pattern):
        log("时间配置: 未发现")
        return

    from bs4 import BeautifulSoup
    from script.common.util import parse_publish_time
    from script.common.datetimeutil import extract_time_text_from_element
    import re

    publish_time = ""
    soup = BeautifulSoup(html, 'html.parser')

    if time_selector:
        time_el = soup.select_one(time_selector)
        if time_el:
            time_text = extract_time_text_from_element(time_el)
            publish_time = parse_publish_time(time_text) or ""

    if not publish_time and pattern:
        match = re.search(pattern, html)
        if match:
            publish_time = parse_publish_time(match.group(0)) or ""

    if time_selector:
        log(f"时间配置: time_selector={time_selector}, pattern={pattern}, 发现时间={publish_time or '未提取到'}")
    else:
        log(f"时间配置: pattern={pattern}, 发现时间={publish_time or '未提取到'}")