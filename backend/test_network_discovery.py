import asyncio, sys, io, os, re
os.environ["NO_COLOR"] = "1"

with open("C:/tmp/net_discovery_test.txt", "w", encoding="utf-8") as f:
    f.write("Starting test\n")
    f.flush()

    base_url = 'http://hy.tencent.com/research'

    from urllib.parse import urlparse
    from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig

    async def _capture_and_discover():
        f.write("Starting crawl\n")
        f.flush()

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
            f.write(f"Crawl success: {result.success}\n")
            f.flush()

        network_requests = getattr(result, 'network_requests', []) or []
        f.write(f"Total network_requests: {len(network_requests)}\n")
        f.flush()

        parsed_base = urlparse(base_url)
        origin = f"{parsed_base.scheme}://{parsed_base.netloc}"

        api_candidates = []
        for i, req in enumerate(network_requests):
            req_url = getattr(req, 'url', None) or (req.get('url') if isinstance(req, dict) else None)
            if not req_url:
                continue
            if re.search(r'\.(js|css|png|jpg|jpeg|gif|svg|woff2?|ico)(\?|$)', req_url, re.I):
                continue
            req_type = getattr(req, 'type', None) or (req.get('type') if isinstance(req, dict) else None) or ''
            is_fetch = req_type in ('fetch', 'xhr', 'request', 'POST', 'GET')
            if is_fetch or '/api/' in req_url or '/blog/' in req_url or 'hunyuan' in req_url:
                api_candidates.append(req_url)

        f.write(f"API candidates: {api_candidates}\n")
        f.flush()

        if not api_candidates:
            f.write("No candidates found\n")
            f.flush()
            return None, None, []

        unique_apis = list(dict.fromkeys(api_candidates))
        f.write(f"Unique APIs: {unique_apis}\n")
        f.flush()

        # Try first API
        import requests
        api_url = unique_apis[0]
        headers = {
            "Origin": f"{urlparse(base_url).scheme}://{urlparse(base_url).netloc}",
            "Referer": base_url,
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json",
        }
        resp = requests.post(api_url, json={"pageNum": 1, "pageSize": 20}, headers=headers, timeout=10)
        f.write(f"POST {api_url}: status={resp.status_code}\n")
        f.flush()
        data = resp.json()
        items = data.get('data', {}).get('list', []) or data.get('list', []) or data.get('data', [])
        f.write(f"Items: {len(items)}\n")
        if items:
            first = items[0]
            slug = first.get("url") or first.get("customUrl") or str(first.get("id", ""))
            title = first.get("title", "")
            base = base_url.rstrip('/')
            full_url = f"{base}/{slug}"
            f.write(f"Full URL: {full_url}\n")
            f.flush()
            return full_url, title, items[:3]
        return None, None, []

    url, title, samples = asyncio.run(_capture_and_discover())
    f.write(f"Final result: url={url}, title={title}\n")
    f.flush()

with open("C:/tmp/net_discovery_test.txt", "r", encoding="utf-8") as f:
    print(f.read())
