"""
content_filter.py - Crawl4AI PruningContentFilter 配置

核心职责：提供 crawl4ai 的 PruningContentFilter 和 DefaultMarkdownGenerator 实例。

正文提取统一使用 clean_article_html + _extract_text_from_cleaned + _strip_trailing_disclaimer，
实现在各调用方（article_crawler.py, fetcher.py, news.py）。

使用方式：
  from script.crawl.content.content_filter import get_content_filter, get_markdown_generator
  filter = get_content_filter()
  generator = get_markdown_generator(filter)
"""

from crawl4ai.content_filter_strategy import PruningContentFilter
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator

# 默认全局过滤器实例（单例，程序生命周期内复用）
_CONTENT_FILTER: PruningContentFilter = None
_MARKDOWN_GENERATOR: DefaultMarkdownGenerator = None


def create_content_filter(
    min_word_threshold: int = 5,
    threshold: float = 0.48,
    threshold_type: str = "fixed",
) -> PruningContentFilter:
    """
    创建 PruningContentFilter 实例。

    参数说明：
      min_word_threshold: 最小词数阈值，低于该值的文本块直接丢弃（默认 5）
      threshold: 固定阈值，分值低于此值的块丢弃（默认 0.48，crawl4ai 推荐值）
      threshold_type: 阈值类型，"fixed" 或 "dynamic"（默认 "fixed"）

    返回：
      PruningContentFilter 实例
    """
    return PruningContentFilter(
        min_word_threshold=min_word_threshold,
        threshold=threshold,
        threshold_type=threshold_type,
    )


def get_content_filter() -> PruningContentFilter:
    """获取全局单例 PruningContentFilter（懒加载）"""
    global _CONTENT_FILTER
    if _CONTENT_FILTER is None:
        _CONTENT_FILTER = create_content_filter()
    return _CONTENT_FILTER


def get_markdown_generator(
    content_filter: PruningContentFilter = None,
) -> DefaultMarkdownGenerator:
    """
    创建配置了内容过滤器的 MarkdownGenerator。

    参数：
      content_filter: PruningContentFilter 实例，传入后 fit_markdown 会自动使用

    返回：
      DefaultMarkdownGenerator 实例，其 generate_markdown() 返回的
      MarkdownGenerationResult.fit_markdown 即为过滤后正文
    """
    if content_filter is None:
        content_filter = get_content_filter()
    return DefaultMarkdownGenerator(content_filter=content_filter)


def get_markdown_generatorSingleton() -> DefaultMarkdownGenerator:
    """获取全局单例 MarkdownGenerator（懒加载）"""
    global _MARKDOWN_GENERATOR
    if _MARKDOWN_GENERATOR is None:
        _MARKDOWN_GENERATOR = get_markdown_generator()
    return _MARKDOWN_GENERATOR


