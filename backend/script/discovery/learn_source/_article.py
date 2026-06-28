# _article.py - 样本文章提取
from script.discovery.list_discovery import log
from script.discovery.util.html_fetch import extract_html_links_with_titles
from script.discovery.util.sample_log import log_sample_news
from script.discovery.util.validation import is_valid_news_sample


def extract_sample_article(
    list_config: dict | None,
    list_html: str,
    name: str,
) -> tuple[str | None, str | None, list]:
    """Step 3: 从 LLM 输出 → extract_article_links → raw HTML 三段式回退提取样本文章 URL"""
    llm_article = list_config.get("article") if list_config else None
    article_url = llm_article.get("url") if llm_article else None
    article_title = llm_article.get("title") if llm_article else None
    sample_news = []

    if article_url:
        return article_url, article_title, sample_news

    # 回退 1: extract_article_links（markdown 模式 [标题](URL)）
    article_url, article_title, sample_news = _try_extract_article_links(list_html, name)
    if article_url:
        return article_url, article_title, sample_news

    # 回退 2: extract_html_links_with_titles（HTML 正则兜底）
    raw_links = extract_html_links_with_titles(list_html)
    if len(raw_links) >= 1:
        article_url = raw_links[0]["url"]
        article_title = raw_links[0].get("title", "")
        sample_news = raw_links[:3]
        log(f"[统一学习] 从 raw HTML 提取到 {len(raw_links)} 条新闻")

    # 输出样本新闻
    valid_samples = [s for s in sample_news if is_valid_news_sample(s)]
    if valid_samples:
        log("[统一学习] 样本新闻（前3条）:")
        log_sample_news(valid_samples, log)

    return article_url, article_title, sample_news


def _try_extract_article_links(list_html: str, name: str) -> tuple[str | None, str | None, list]:
    """回退 1：extract_article_links 提取并筛选有效样本"""
    from script.discovery.article_link_extractor import extract_article_links
    try:
        articles = extract_article_links(list_html, name, html=list_html)
    except Exception as e:
        log(f"[统一学习] extract_article_links 失败: {e}")
        return None, None, []

    if not articles:
        return None, None, []

    valid_articles = [a for a in articles if is_valid_news_sample(a)]
    if valid_articles:
        log(f"[统一学习] 从 extract_article_links 提取到 {len(articles)} 条新闻，找到 {len(valid_articles)} 条有效")
        return valid_articles[0].get("url"), valid_articles[0].get("title"), valid_articles[:3]

    return None, None, articles[:3]