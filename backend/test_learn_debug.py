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
print('Result type:', type(result))
print('article_url:', result.get('article_url'))
print('article_title:', result.get('article_title'))
print('list_complete:', result.get('list_complete'))
print('source_type:', result.get('source_type'))
