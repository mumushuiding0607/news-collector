# _crawl4ai.py - crawl4ai 集成（已废弃，仅保留导入结构）
#
# extract_clean_content 已删除，统一正文提取逻辑为：
#   clean_article_html + _extract_text_from_cleaned + _strip_trailing_disclaimer
# 该逻辑已实现在各调用方（article_crawler.py, fetcher.py, news.py）
