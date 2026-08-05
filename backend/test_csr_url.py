import asyncio, sys, io, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from script.discovery.util.html_fetch import fetch_list_html

result = asyncio.run(fetch_list_html('http://hy.tencent.com/research'))
html = result[1]

js_files = re.findall(r'href="(https://hunyuan-blog-web-prod[^"]+\.js)"', html)
main_js = [f for f in js_files if 'index' in f and 'vendor' not in f]

all_slugs = set()
if main_js:
    import urllib.request
    try:
        resp = urllib.request.urlopen(main_js[0], timeout=10)
        js_content = resp.read().decode('utf-8', errors='ignore')
        # 搜索所有可能的 slug 模式
        slugs = re.findall(r'/(?:research|lab|article|post)/([a-zA-Z0-9_-]+)', js_content)
        all_slugs.update(slugs)
        # 搜索 "hy-" 前缀的 slug
        hy_slugs = re.findall(r'"(hy[a-zA-Z0-9_-]+)"', js_content)
        all_slugs.update(hy_slugs)
        print('All slugs found:', sorted(all_slugs)[:20])
        print('Total unique slugs:', len(all_slugs))

        # 尝试拼接几个 URL 测试
        base = 'https://hy.tencent.com'
        for slug in list(all_slugs)[:5]:
            print(f'Test URL: {base}/research/{slug}')
    except Exception as e:
        print('Fetch JS failed:', e)
