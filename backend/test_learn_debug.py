import asyncio, sys, io, os
os.environ["NO_COLOR"] = "1"
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from script.discovery.learn_source import learn_source_config
result = learn_source_config(
    url='http://hy.tencent.com/research',
    name='腾讯研究院',
    force_relearn=True,
)
print(f"article_url: {result.get('article_url')}")
print(f"article_title: {result.get('article_title', '')[:40] if result.get('article_title') else 'None'}")
print(f"list_complete: {result.get('list_complete')}")
print(f"content_extract: {result.get('content_extract', {})}")
