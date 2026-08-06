import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 设置 AI新闻 DB
from script.db.db_selector import ensure_db
ensure_db('AI新闻')

# 强制重新加载配置
import script.crawl.crawl_config as cc
cc._cached_config = None

from script.crawl.crawl_config import get_crawl_config
cfg = get_crawl_config()
print(f"titleMinLength: {cfg['titleMinLength']}")
print(f"days: {cfg['days']}")
print(f"skipIfNoDate: {cfg['skipIfNoDate']}")
