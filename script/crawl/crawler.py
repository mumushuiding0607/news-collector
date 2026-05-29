"""
crawler.py - 新闻采集入口

按顺序执行三步：
  Step 1: list_crawler  - 采集列表页（标题/日期/摘要）
  Step 2: news_filter   - LLM 过滤（判断是否有用）
  Step 3: article_crawler - 增量采集文章正文

使用：
  python -m crawl.crawler      # 执行全流程
  python -m crawl.list_crawler   # 单独运行 Step 1
  python -m crawl.news_filter    # 单独运行 Step 2
  python -m crawl.article_crawler # 单独运行 Step 3
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from .list_crawler import main as list_crawler_main
from .news_filter import main as news_filter_main
from .article_crawler import main as article_crawler_main


def main():
    print("=" * 60)
    print("新闻采集全流程")
    print("=" * 60)

    print("\n>>> Step 1: 采集列表页")
    asyncio.run(list_crawler_main())

    print("\n>>> Step 2: LLM 过滤")
    asyncio.run(news_filter_main())

    print("\n>>> Step 3: 增量采集文章正文")
    asyncio.run(article_crawler_main())

    print("\n" + "=" * 60)
    print("全部流程完成")
    print("=" * 60)


if __name__ == "__main__":
    main()