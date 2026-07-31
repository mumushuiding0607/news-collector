"""
html_text_sanitizer.py - HTML 文本脱敏工具

用途：把 HTML 里的用户文本替换为中性占位符，**仅保留 DOM 结构**，
     避免 LLM 代理层因政治/敏感词直接拒答（HTTP 500 "output new_sensitive"）。

设计原则：
- 保留：标签、class、id、href、src、URL 本身（LLM 用来分析 CSS 选择器）
- 替换：所有可见文本节点（h*/a/span/p/div/li/em/time 等）
- 占位符使用稳定且无敏感含义的中性字串（标题样例/摘要样例/日期样例/普通文字）

用法：
    from script.discovery.util.html_text_sanitizer import sanitize_html_for_llm
    safe_html = sanitize_html_for_llm(html)
"""

from bs4 import BeautifulSoup, NavigableString

# 完全跳过文本替换的标签（其内容不会参与选择器分析）
_SKIP_TAGS = frozenset({"script", "style", "noscript", "meta", "link", "title", "head", "html"})

# 标题类标签：用 __HEADING__ 替换（特殊占位符让 LLM 能识别这是语义标题）
_TITLE_TAGS = frozenset({"h1", "h2", "h3", "h4", "h5", "h6"})

# 日期/时间类标签：用"日期样例"替换
_DATETIME_TAGS = frozenset({"em", "time", "b", "i", "strong"})

# 摘要类标签：用"摘要样例"替换
_SUMMARY_TAGS = frozenset({"span", "p"})

# 链接内文本：用"链接文字样例"替换
_ANCHOR_TAG = "a"

# 列表项内文本：用"列表项样例"替换
_LI_TAG = "li"


def _placeholder_for(tag_name: str) -> str:
    """根据标签类型返回对应占位符"""
    if tag_name in _TITLE_TAGS:
        return "__HEADING__"
    if tag_name in _DATETIME_TAGS:
        return "日期样例"
    if tag_name in _SUMMARY_TAGS:
        return "摘要样例"
    if tag_name == _ANCHOR_TAG:
        return "链接文字样例"
    if tag_name == _LI_TAG:
        return "列表项文字样例"
    return "普通文字样例"


def _placeholder_for_text(tag) -> str:
    """
    根据标签类型和文本内容返回对应占位符。
    如果标签是摘要类（p/span），但文本包含日期，返回日期占位符。
    对于 p 标签，保留第一个 CSS 类名作为区分（如 p.text-md → 日期样例[text-md]）。
    """
    tag_name = tag.name
    base = _placeholder_for(tag_name)

    # 摘要类标签但文本包含日期 → 标记为日期
    if tag_name in _SUMMARY_TAGS:
        text = tag.get_text(strip=True)
        if text:
            from script.common.datetimeutil import DATETIME_REGEX
            if DATETIME_REGEX.search(text):
                # 提取第一个 CSS 类名用于区分
                classes = tag.get('class', [])
                cls_suffix = f"[{classes[0]}]" if classes else ""
                return f"日期样例{cls_suffix}"

    # p 标签有 CSS 类时，在占位符中保留类名以便 LLM 区分
    if tag_name == 'p':
        classes = tag.get('class', [])
        if classes:
            cls_suffix = f"[{classes[0]}]"
            # 日期类（已有）或 摘要类
            if "日期样例" in base:
                return f"日期样例{cls_suffix}"
            else:
                return f"摘要样例{cls_suffix}"

    return base


def sanitize_html_for_llm(html: str) -> str:
    """
    把 HTML 中的可见文本替换为中性占位符，保留 DOM 结构。

    只替换直接文本节点（不递归进入子标签的文本），
    这样像 `<a><h3>真实标题</h3></a>` 会变成 `<a><h3>标题样例</h3></a>`，
    而 `<a>前缀<h3>真实标题</h3>后缀</a>` 中 <a> 的前后文本会被替换为"链接文字样例"。

    多次出现相同类型的占位符时会附加编号，避免完全重复字符串可能触发更严的命中检测。

    Args:
        html: 原始 HTML 字符串

    Returns:
        脱敏后的 HTML 字符串（结构未变，文本已替换）
    """
    if not html:
        return html

    soup = BeautifulSoup(html, "html.parser")

    # 计数：避免大量相同字符串重复
    counters: dict[str, int] = {}

    for tag in soup.find_all(True):
        if tag.name in _SKIP_TAGS:
            continue

        # 收集直接文本节点
        direct_text_nodes = [
            child for child in tag.children
            if isinstance(child, NavigableString) and child.strip()
        ]
        if not direct_text_nodes:
            continue

        base = _placeholder_for_text(tag)
        n = counters.get(base, 0)
        replacement = f"{base}{n}" if n > 0 else base
        counters[base] = n + 1

        # 用单个文本节点替换所有直接文本，保留空白
        # 用空格包裹确保 text node 在 HTML 输出中清晰可见
        new_text = NavigableString(f" {replacement} ")
        # 把第一个文本节点换成新文本，其余清空
        direct_text_nodes[0].replace_with(new_text)
        for node in direct_text_nodes[1:]:
            node.replace_with(NavigableString(""))

    return str(soup)
