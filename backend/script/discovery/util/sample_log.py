# sample_log.py - 样本新闻日志工具
#
# 统一格式化输出样本新闻列表。
#
# 使用方式：
#   from script.discovery.util.sample_log import log_sample_news


def log_sample_news(news_list: list, log_fn=None, max_count: int = 3):
    """
    格式化输出样本新闻列表。

    每条格式：  [index] 标题 | 发布日期

    Args:
        news_list: 新闻样本列表（支持 dict 或有 title/url/publish_time 属性的对象）
        log_fn: 日志函数（默认 print）
        max_count: 最多输出条数（默认3）
    """
    if log_fn is None:
        def log_fn(msg):
            print(msg)
    if not news_list:
        return
    for i, news in enumerate(news_list[:max_count], 1):
        # 支持 dict 或有属性的对象
        if hasattr(news, 'get'):
            title = news.get("title", "")
            publish_time = news.get("publish_time", "") or news.get("time", "")
        else:
            title = getattr(news, 'title', '')
            publish_time = getattr(news, 'publish_time', '') or getattr(news, 'time', '')
        log_fn(f"  [{i}] {title} | {publish_time}")