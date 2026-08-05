import asyncio, sys, io, os, re, json
os.environ["NO_COLOR"] = "1"
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

base_url = 'http://hy.tencent.com/research'

from urllib.parse import urlparse, urljoin

async def _capture_and_discover():
    from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig

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
            print("FAIL: arun not success")
            return None, None, []

    network_requests = getattr(result, 'network_requests', []) or []
    print(f"Total network_requests: {len(network_requests)}")

    parsed_base = urlparse(base_url)
    origin = f"{parsed_base.scheme}://{parsed_base.netloc}"

    api_candidates = []
    for req in network_requests:
        req_url = getattr(req, 'url', None) or (req.get('url') if isinstance(req, dict) else None)
        if not req_url:
            continue
        if re.search(r'\.(js|css|png|jpg|jpeg|gif|svg|woff2?|ico)(\?|$)', req_url, re.I):
            continue
        req_type = getattr(req, 'type', None) or (req.get('type') if isinstance(req, dict) else None) or ''
        if req_type in ('fetch', 'xhr', 'request', 'POST', 'GET') or '/api/' in req_url or '/blog/' in req_url or 'hunyuan' in req_url:
            api_candidates.append(req_url)

    print(f"API candidates: {api_candidates}")
    if not api_candidates:
        return None, None, []

    unique_apis = list(dict.fromkeys(api_candidates))
    print(f"Unique APIs: {unique_apis}")

    for api_url in unique_apis:
        items = _try_api_with_samples(api_url, base_url)
        print(f"API {api_url}: {len(items)} items")
        if items:
            first = items[0]
            print(f"  first: {first}")
            article_url = first.get("url") or first.get("customUrl") or str(first.get("id", ""))
            article_title = first.get("title", "")
            if article_url:
                if article_url.startswith("http"):
                    full_url = article_url
                else:
                    full_url = urljoin(origin, article_url)
                print(f"  full_url: {full_url}")
                return full_url, article_title, items[:3]

    return None, None, []


def _try_api_with_samples(api_url, base_url):
    import requests
    headers = {
        "Origin": f"{urlparse(base_url).scheme}://{urlparse(base_url).netloc}",
        "Referer": base_url,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json, text/plain, */*",
    }
    try:
        resp = requests.post(api_url, json={"pageNum": 1, "pageSize": 20}, headers=headers, timeout=10)
        print(f"  POST {api_url}: status={resp.status_code}")
        if resp.status_code != 200:
            return []
        data = resp.json()
    except Exception as e:
        print(f"  Exception: {e}")
        return []

    items = _extract_items_from_api_response(data)
    for item in items:
        url_field = item.get("url") or item.get("customUrl") or item.get("slug") or item.get("path")
        if url_field:
            item["url"] = url_field
    return items


def _extract_items_from_api_response(data):
    if isinstance(data, dict):
        for key in ("data", "list", "items", "records", "result"):
            if key in data and isinstance(data[key], list) and data[key]:
                return data[key]
        inner = data.get("data")
        if isinstance(inner, dict):
            for key in ("list", "items", "records", "result"):
                if key in inner and isinstance(inner[key], list) and inner[key]:
                    return inner[key]
    elif isinstance(data, list):
        return data
    return []


url, title, samples = asyncio.run(_capture_and_discover())
print(f"\nResult: url={url}, title={title}")
