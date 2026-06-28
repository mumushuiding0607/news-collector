# html_truncate.py - HTML 安全截断工具
#
# 在尽可能保留完整标签的前提下截断 HTML，避免 LLM 看到残缺的开始/结束标签。

MAX_HTML_SIZE = 50 * 1024


def safe_truncate(html: str, max_size: int) -> str:
    """
    安全截断 HTML，优先在最近的 </ 后切断，兜底在最近的 > 后切断。

    Args:
        html: 原始 HTML
        max_size: 最大允许长度

    Returns:
        截断后的 HTML（长度 <= max_size）
    """
    if len(html) <= max_size:
        return html

    truncated = html[:max_size]
    safe_cutoff = truncated.rfind('</')
    if safe_cutoff > max_size // 2:
        return truncated[:safe_cutoff + 1]

    safe_cutoff = truncated.rfind('>')
    if safe_cutoff > max_size // 2:
        return truncated[:safe_cutoff + 1]

    return truncated