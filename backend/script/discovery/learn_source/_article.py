# _article.py - 样本文章提取
from script.discovery.list_discovery import log
from script.discovery.util.html_fetch import extract_html_links_with_titles
from script.discovery.util.sample_log import log_sample_news
from script.discovery.util.validation import is_valid_news_sample


def _set_url_pattern(list_config: dict, article_url: str) -> None:
    """从样本 article_url 提取 url_pattern 并更新到 list_config。

    例如 article_url="http://hy.tencent.com/research/hyra"
    → url_pattern="http://hy.tencent.com/research/{slug}"
    """
    from urllib.parse import urlparse
    parsed = urlparse(article_url)
    # 提取路径部分，如 "/research/hyra" → 变成 "/research/{slug}"
    path_parts = parsed.path.rstrip('/').split('/')
    if path_parts:
        path_parts[-1] = '{slug}'
        pattern_path = '/'.join(path_parts)
        # 重建 URL：scheme + netloc + pattern_path
        url_pattern = f"{parsed.scheme}://{parsed.netloc}{pattern_path}"
        list_config['url_pattern'] = url_pattern
        if list_config.get('type') != 'api':
            list_config['type'] = 'api'  # 标记为 API 类型，便于区分处理
        log(f"[统一学习] 发现 url_pattern: {url_pattern}")


def extract_sample_article(
    list_config: dict | None,
    list_html: str,
    name: str,
    base_url: str = "",
) -> tuple[str | None, str | None, list]:
    """Step 3: 从 LLM 输出 → extract_article_links → raw HTML → 网络捕获 四段式回退提取样本文章 URL"""
    import re as _re
    llm_article = list_config.get("article") if list_config else None
    article_url = llm_article.get("url") if llm_article else None
    article_title = llm_article.get("title") if llm_article else None
    sample_news = []

    # 判断 LLM 返回的 URL 是否为占位符（如 /article/1）
    def _is_placeholder(url):
        if not url:
            return True
        if _re.match(r'.*/(article|news|detail|view|page|p)\s*/\d+$', url, _re.IGNORECASE):
            return True
        if '标题样例' in (article_title or ''):
            return True
        return False

    # 如果 LLM 返回的是占位符，忽略它，继续往后走（尝试网络捕获）
    if article_url and _is_placeholder(article_url):
        log(f"[统一学习] LLM 返回占位符 URL: {article_url}，跳过继续往后")
        article_url = None

    if article_url:
        # 从 LLM 分析发现的 URL 提取 url_pattern
        if list_config and not list_config.get('url_pattern'):
            _set_url_pattern(list_config, article_url)
        return article_url, article_title, sample_news

    # 回退 1: extract_article_links（markdown 模式 [标题](URL)）
    article_url, article_title, sample_news = _try_extract_article_links(list_html, name)
    if article_url:
        return article_url, article_title, sample_news

    # 回退 2: extract_html_links_with_titles（HTML 正则兜底）
    raw_links = extract_html_links_with_titles(list_html)
    if len(raw_links) >= 1:
        article_url = raw_links[0]["url"]
        article_title = raw_links[0].get("title", "")
        sample_news = raw_links[:3]
        log(f"[统一学习] 从 raw HTML 提取到 {len(raw_links)} 条新闻")

    # 回退 3: 网络请求捕获发现 API（CSR 页，API 不在 HTML 源码中）
    if not article_url and base_url:
        article_url, article_title, sample_news = _try_network_capture_discovery(base_url, list_config)
        if article_url:
            print(f"[DEBUG network capture] found article_url={article_url}", file=__import__('sys').stderr)
            # 从样本 URL 提取 url_pattern
            if list_config and not list_config.get('url_pattern'):
                print(f"[DEBUG before _set_url_pattern] list_config id={id(list_config)}, url_pattern={list_config.get('url_pattern')}", file=__import__('sys').stderr)
                _set_url_pattern(list_config, article_url)
                print(f"[DEBUG after _set_url_pattern] list_config id={id(list_config)}, url_pattern={list_config.get('url_pattern')}", file=__import__('sys').stderr)
            # 把发现的 article URL/title 存回 list_config（方便后续保存到 DB）
            if list_config is not None:
                list_config['article'] = {"url": article_url, "title": article_title or ""}
            return article_url, article_title, sample_news

    # 输出样本新闻
    valid_samples = [s for s in sample_news if is_valid_news_sample(s)]
    if valid_samples:
        log("[统一学习] 样本新闻（前3条）:")
        log_sample_news(valid_samples, log)

    return article_url, article_title, sample_news


def _try_extract_article_links(list_html: str, name: str) -> tuple[str | None, str | None, list]:
    """回退 1：extract_article_links 提取并筛选有效样本"""
    from script.discovery.article_link_extractor import extract_article_links
    try:
        articles = extract_article_links(list_html, name, html=list_html)
    except Exception as e:
        log(f"[统一学习] extract_article_links 失败: {e}")
        return None, None, []

    if not articles:
        return None, None, []

    valid_articles = [a for a in articles if is_valid_news_sample(a)]
    if valid_articles:
        log(f"[统一学习] 从 extract_article_links 提取到 {len(articles)} 条新闻，找到 {len(valid_articles)} 条有效")
        return valid_articles[0].get("url"), valid_articles[0].get("title"), valid_articles[:3]

    return None, None, articles[:3]


def _try_network_capture_discovery(
    base_url: str,
    list_config: dict | None,
) -> tuple[str | None, str | None, list]:
    """
    回退 3: 网络请求捕获发现 API（CSR 页）。

    用于纯 CSR/JS 渲染页面，API 调用不在 HTML 源码中。
    通过 crawl4ai 的 capture_network_requests 监控渲染阶段的 fetch/XHR 调用，
    捕获文章列表 API，再从中提取第一篇文章的 URL。
    """
    import asyncio, json, re
    from urllib.parse import urlparse

    try:
        from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
    except ImportError:
        return None, None, []

    parsed_base = urlparse(base_url)

    async def _capture_and_discover():
        async with AsyncWebCrawler(config=BrowserConfig(headless=True)) as crawler:
            result = await crawler.arun(
                url=base_url,
                config=CrawlerRunConfig(
                    delay_before_return_html=5.0,
                    page_timeout=30000,
                    verbose=False,
                    capture_network_requests=True,
                ),
            )
            if not result.success:
                return None, None, []

        # 从 network_requests 中提取 API URL
        network_requests = getattr(result, 'network_requests', []) or []
        if hasattr(result, 'results') and result.results:
            network_requests = getattr(result.results[0], 'network_requests', []) or []

        api_candidates = []
        for req in network_requests:
            req_url = getattr(req, 'url', None) or (req.get('url') if isinstance(req, dict) else None)
            if not req_url:
                continue
            # 跳过静态资源
            if re.search(r'\.(js|css|png|jpg|jpeg|gif|svg|woff2?|ico)(\?|$)', req_url, re.I):
                continue
            # 扩大范围：任何 fetch/XHR 请求或包含 api/blog 的 URL
            req_type = getattr(req, 'type', None) or (req.get('type') if isinstance(req, dict) else None) or ''
            is_fetch = req_type in ('fetch', 'xhr', 'request', 'POST', 'GET')
            if is_fetch or '/api/' in req_url or '/blog/' in req_url or 'hunyuan' in req_url:
                api_candidates.append(req_url)

        if not api_candidates:
            log(f"[统一学习] 网络捕获：未发现 API 请求（total={len(network_requests)}）")
            return None, None, []

        log(f"[统一学习] 网络捕获：发现 {len(api_candidates)} 个候选 API，开始验证")
        unique_apis = list(dict.fromkeys(api_candidates))

        # 对每个候选 API 发测试请求
        for api_url in unique_apis:
            items = _try_api_with_samples(api_url, base_url)
            if items:
                first = items[0]
                # 提取 slug/id 用于拼装 URL
                slug = first.get("url") or first.get("customUrl") or first.get("slug") or str(first.get("id", ""))
                article_title = first.get("title", "")
                if slug:
                    # 拼装完整 URL：base_url 末尾通常就是列表页路径（如 /research），
                    # 只需要追加 slug。处理 base_url 可能带或不带末尾斜杠
                    base = base_url.rstrip('/')
                    full_url = f"{base}/{slug}"
                    log(f"[统一学习] 网络捕获发现文章 URL: {full_url}")
                    return full_url, article_title, items[:3]

        return None, None, []

    try:
        url, title, samples = asyncio.run(_capture_and_discover())
        return url, title, samples
    except Exception as e:
        log(f"[统一学习] 网络捕获异常: {e}")
        return None, None, []


def _try_api_with_samples(api_url: str, base_url: str) -> list[dict]:
    """对候选 API 发请求，验证返回并提取文章列表"""
    import json, requests
    from urllib.parse import urlparse

    # 处理相对 URL
    if api_url.startswith("/"):
        parsed = urlparse(base_url)
        api_url = f"{parsed.scheme}://{parsed.netloc}{api_url}"

    parsed_base = urlparse(base_url)
    headers = {
        "Origin": f"{parsed_base.scheme}://{parsed_base.netloc}",
        "Referer": base_url,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json, text/plain, */*",
    }

    try:
        resp = requests.post(
            api_url,
            json={"pageNum": 1, "pageSize": 20},
            headers=headers,
            timeout=10,
        )
        if resp.status_code != 200:
            return []
        data = resp.json()
    except Exception:
        return []

    # 提取文章列表（兼容多种响应格式）
    items = _extract_items_from_api_response(data)
    if not items:
        return []

    # 提取 URL 字段（id/customUrl/slug 等）
    for item in items:
        url_field = item.get("url") or item.get("customUrl") or item.get("slug") or item.get("path")
        if url_field:
            item["url"] = url_field

    return items


def _extract_items_from_api_response(data: dict | list) -> list[dict]:
    """从 API 响应中提取文章列表"""
    if isinstance(data, dict):
        # 常见分页格式
        for key in ("data", "list", "items", "records", "result"):
            if key in data and isinstance(data[key], list):
                items = data[key]
                if items and len(items) > 0:
                    return items
        # 兼容 { data: { list: [...] } } 格式
        inner = data.get("data")
        if isinstance(inner, dict):
            for key in ("list", "items", "records", "result"):
                if key in inner and isinstance(inner[key], list):
                    return inner[key]
    elif isinstance(data, list):
        return data
    return []
