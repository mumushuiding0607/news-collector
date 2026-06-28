# css_selector.py - CSS 选择器构建工具
#
# 从新闻列表提取结果构建 CSS 选择器。
#
# 使用方式：
#   from script.discovery.util.css_selector import build_css_selector


def build_css_selector(result) -> str:
    """
    从提取结果构建 CSS 选择器字符串。

    优先使用已有的 item_selector，否则根据 container_tag + item_tag 构造。

    Args:
        result: 有 .item_selector / .item_tag / .list_container_tag 属性的对象

    Returns:
        CSS 选择器字符串
    """
    if result.item_selector:
        return result.item_selector

    tag = result.item_tag or "a"
    container_tag = result.list_container_tag or "div"
    return f"{container_tag} {tag}[href]"