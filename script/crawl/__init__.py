"""
crawl/ - 新闻采集模块

子模块：
  list_crawler    - Step 1: 采集列表页（标题/日期/摘要）
  news_filter     - Step 2: LLM 过滤（判断是否有用）
  article_crawler - Step 3: 增量采集文章正文
  crawler         - 入口，按序执行三步
"""

from .crawler import main

__all__ = ["main"]