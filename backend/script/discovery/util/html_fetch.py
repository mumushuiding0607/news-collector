# html_fetch.py - 渲染 HTML 抓取工具
#
# 使用 crawl4ai 获取渲染后的 HTML（统一入口，所有爬虫/采集/API 都走这里）。
#
# 使用方式：
#   from script.discovery.util.html_fetch import fetch_rendered_html
#   url, html = asyncio.run(fetch_rendered_html("https://example.com"))
#   url, html, markdown = await fetch_rendered_html(url, return_markdown=True)

import asyncio
import re
from typing import AsyncIterator

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig

# Default CCTV news link pattern
CCTV_LINK_PATTERN = re.compile(
    r'href=["\'](https?://tv\.cctv\.com/\d{4}/\d{2}/\d{2}/[^"\']+)["\']',
    re.I,
)

# 通用 wait_for 常量：适用于绝大多数中文新闻文章页（语义级元素选择）
# 列表页不再使用 selector-based wait，改为固定 delay（见 fetch_list_html）。
# 文章页保留 selector wait（"article"/".article-content"等是公认标准类名，不会变）。
DEFAULT_ARTICLE_WAIT = (
    "js:() => document.querySelector("
    "'article, .article-content, #content, main, .content, "
    "'#article, .main-content, .TRS_Editor, #article-content, .text'"
    ") !== null"
)

# 列表页：等 DOMContentLoaded 后再多等 1.5s 让 JS 执行（bounded，无无限等待）
DEFAULT_LIST_DELAY_SECONDS = 1.5


async def fetch_list_html(
    url: str,
    return_markdown: bool = False,
    crawler: "AsyncWebCrawler | None" = None,
    page_timeout: int = 30000,
    wait_for: str | None = None,
    delay: float | None = None,
    log_fn=None,
):
    """
    列表页抓取的语义化入口。

    默认策略：等 DOMContentLoaded + 固定 delay（DEFAULT_LIST_DELAY_SECONDS），
    bounded（不会无限等待），对静态页几乎无额外开销，对 JS 渲染页有合理等待。

    特殊场景可显式传 wait_for（selector-based）覆盖默认 delay 策略，
    但需自行承担 selector 不匹配时 wait_for_timeout 超时的风险。

    API 模式的数据源请直接调 crawl_api_source，不要走本函数（无意义）。
    """
    if delay is None:
        delay = DEFAULT_LIST_DELAY_SECONDS
    return await fetch_rendered_html(
        url,
        wait_for=wait_for,
        delay_before_return_html=delay,
        return_markdown=return_markdown,
        crawler=crawler,
        page_timeout=page_timeout,
        log_fn=log_fn,
    )


async def fetch_article_html(
    url: str,
    return_markdown: bool = False,
    crawler: "AsyncWebCrawler | None" = None,
    page_timeout: int = 30000,
    wait_for: str | None = None,
    log_fn=None,
):
    """
    文章页抓取的语义化入口：默认等常见正文容器出现（DEFAULT_ARTICLE_WAIT）。

    如果站点正文容器不在默认列表里，可传 wait_for 自定义。
    """
    if wait_for is None:
        wait_for = DEFAULT_ARTICLE_WAIT
    return await fetch_rendered_html(
        url,
        wait_for=wait_for,
        return_markdown=return_markdown,
        crawler=crawler,
        page_timeout=page_timeout,
        log_fn=log_fn,
    )


async def fetch_rendered_html(
    url: str,
    wait_for: str | None = None,
    page_timeout: int = 30000,
    return_markdown: bool = False,
    crawler: AsyncWebCrawler | None = None,
    delay_before_return_html: float | None = None,
    log_fn=None,
) -> tuple[str, str] | tuple[str, str, str]:
    """
    使用 crawl4ai 抓取单个 URL，返回 (url, html) 或 (url, html, markdown)。

    这是项目内所有 HTML 抓取的**唯一入口**（API、测试、生产采集都走这里），
    不要在其他模块内联使用 AsyncWebCrawler / CrawlerRunConfig。

    Args:
        url: 目标 URL
        wait_for: 可选，等待条件（selector-based，crawl4ai 语法）。
                  列表页默认不传（用 delay_before_return_html 代替）；
                  文章页用 DEFAULT_ARTICLE_WAIT。
                  注意：selector 不匹配时可能等满 page_timeout，建议优先用 delay。
        page_timeout: 页面加载超时（毫秒），默认 30s
        return_markdown: 是否同时返回 markdown（生产 list 提取逻辑同时依赖 html 和 markdown）
        crawler: 可选的 AsyncWebCrawler 实例（生产批量采集复用同一个浏览器进程，
                 避免每条 URL 启停 Chromium；None 则内部创建新的）
        delay_before_return_html: 可选，DOMContentLoaded 之后额外等多少秒再取 HTML，
                  适合 JS 渲染页。bounded（不会无限等）。None 时不设。
        log_fn: 日志函数（默认 None 不打印）

    Returns:
        (url, html) 或 (url, html, markdown)；html/markdown 为空字符串表示抓取失败
    """
    if log_fn is None:
        def log_fn(msg):
            pass

    run_config_kwargs = dict(
        word_count_threshold=20,
        verbose=False,
        page_timeout=page_timeout,
    )
    if wait_for:
        run_config_kwargs["wait_for"] = wait_for
    if delay_before_return_html is not None:
        run_config_kwargs["delay_before_return_html"] = delay_before_return_html

    async def _do_fetch(c: AsyncWebCrawler):
        result = await c.arun(url=url, config=CrawlerRunConfig(**run_config_kwargs))
        if result.success:
            log_fn(f"[抓取] 成功: {url}, HTML长度={len(result.html)}")
            if return_markdown:
                return url, result.html, result.markdown or ""
            return url, result.html
        else:
            log_fn(f"[抓取] 失败: {url}")
            if return_markdown:
                return url, "", ""
            return url, ""

    if crawler is not None:
        return await _do_fetch(crawler)
    async with AsyncWebCrawler(config=BrowserConfig(headless=True)) as c:
        return await _do_fetch(c)


def extract_html_links(html: str, pattern: str | re.Pattern = None) -> list[str]:
    """
    从原始 HTML 中提取新闻链接。

    Args:
        html: HTML 原始字符串
        pattern: 可选，正则模式字符串或编译后的 re.Pattern。
                 默认匹配 tv.cctv.com 日期路径格式。

    Returns:
        链接列表（去重，保留顺序）
    """
    compiled = CCTV_LINK_PATTERN if pattern is None else (re.compile(pattern, re.I) if isinstance(pattern, str) else pattern)
    links = compiled.findall(html)
    return list(dict.fromkeys(links))


def extract_html_links_with_titles(html: str, pattern: str | re.Pattern = None) -> list[dict]:
    """
    从原始 HTML 中提取新闻链接及标题。

    Args:
        html: HTML 原始字符串
        pattern: 可选，href 正则模式。默认匹配 tv.cctv.com。

    Returns:
        [{"title": ..., "url": ..., "publish_time": ""}, ...]
    """
    compiled = CCTV_LINK_PATTERN if pattern is None else (re.compile(pattern, re.I) if isinstance(pattern, str) else pattern)
    links = compiled.findall(html)
    if not links:
        return []

    unique_links = list(dict.fromkeys(links))
    results = []
    for link in unique_links[:3]:
        escaped = re.escape(link)
        m = re.search(rf'<a[^>]+href=["\']?{escaped}["\']?[^>]*>([^<]+)</a>', html, re.I)
        title = m.group(1).strip() if m else link.split('/')[-1]
        results.append({"title": title, "url": link, "publish_time": ""})
    return results