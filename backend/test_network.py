import asyncio, sys, io, os
os.environ["NO_COLOR"] = "1"

with open("C:/tmp/net_test_out.txt", "w", encoding="utf-8") as f_out:
    from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
    import re

    async def test():
        base_url = 'http://hy.tencent.com/research'
        async with AsyncWebCrawler(config=BrowserConfig(headless=True, verbose=False)) as crawler:
            result = await crawler.arun(
                url=base_url,
                config=CrawlerRunConfig(
                    delay_before_return_html=5.0,
                    page_timeout=30000,
                    verbose=False,
                    capture_network_requests=True,
                ),
            )

        nr = getattr(result, 'network_requests', []) or []
        f_out.write(f"Total: {len(nr)}\n\n")

        api_candidates = []
        for i, r in enumerate(nr):
            if not isinstance(r, dict):
                continue
            req_url = r.get('url', '')
            if not req_url:
                continue
            if re.search(r'\.(js|css|png|jpg|jpeg|gif|svg|woff2?|ico)(\?|$)', req_url, re.I):
                continue
            req_type = r.get('type', '') or ''
            if req_type in ('fetch', 'xhr', 'request', 'POST', 'GET') or '/api/' in req_url or '/blog/' in req_url:
                api_candidates.append((i, req_type, req_url))

        f_out.write(f"API candidates: {len(api_candidates)}\n")
        for i, t, u in api_candidates:
            f_out.write(f"  req {i}: type={t}, url={u}\n")

    asyncio.run(test())
