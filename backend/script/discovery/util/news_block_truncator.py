# news_block_truncator.py - 新闻块 HTML 截断
#
# 列表发现场景下，把 HTML 裁剪为只保留前 N 个新闻块的结构，节省 LLM token。
#
# 策略：
# 1. 找到所有新闻链接 <a>
# 2. 按顶级列表块（body 直系子元素）分组，排除嵌套的子列表块
# 3. 对每个块：精细化移除子块中不需要的项（不丢失保留内容）
# 4. 超出 max_size 时按完整标签安全截断

import re

from bs4 import BeautifulSoup

from script.discovery.util.html_truncate import safe_truncate
from script.common.datetimeutil import DATETIME_REGEX
from script.discovery.html_cleaner._patterns_a import NEWS_URL_REGEX

# 默认保留的新闻块数量
DEFAULT_NEWS_BLOCK_COUNT = 3

# 复用 html_cleaner 的 URL 模式
_NEWS_URL_RE = NEWS_URL_REGEX

# 容器 class 关键词（分值高）
_CONTAINER_KW = ["item", "container", "list", "entry", "row", "card", "post", "news",
                  "box", "hot", "sidebar", "rank", "ranklist", "listitem"]
# 内容 class 关键词（分值低）
_CONTENT_KW = ["info", "content", "text", "body", "main", "header", "footer", "title", "time", "date"]


def _is_news_link(a_tag) -> bool:
    """判断 <a> 是否是新闻链接"""
    href = a_tag.get("href", "")
    return bool(_NEWS_URL_RE.search(href)) if href else False


def _get_container_score(tag) -> int:
    """
    根据 class 名称给容器打分，分数越高越可能是新闻项容器。
    """
    if tag.name not in ("li", "tr", "div", "article", "section"):
        return -1
    class_str = " ".join(tag.get("class", [])).lower()
    has_container_kw = any(kw in class_str for kw in _CONTAINER_KW)
    has_content_kw = any(kw in class_str for kw in _CONTENT_KW)
    if has_container_kw and not has_content_kw:
        return 2
    elif has_container_kw:
        return 1
    elif has_content_kw:
        return 0
    return -1


def _has_datetime_in_text(element) -> bool:
    """检查元素文本是否包含日期/时间"""
    text = element.get_text()
    return bool(DATETIME_REGEX.search(text)) if text else False


def _has_datetime_in_ancestors(tag, max_depth=10) -> bool:
    """检查元素本身或祖先元素是否包含日期/时间文本"""
    current = tag
    depth = 0
    while current and depth < max_depth:
        if _has_datetime_in_text(current):
            return True
        current = current.parent
        depth += 1
    return False


def _find_item_container(a_tag, requires_datetime=True) -> tuple:
    """
    从新闻链接向上找"新闻项容器"。

    requires_datetime:
        True  = 要求包含 datetime（适用于 live/排行等有时间戳的列表）
        False = 不要求 datetime（适用于普通新闻列表）
    """
    candidates = []
    parent = a_tag.parent
    depth = 0
    while parent and depth < 20:
        score = _get_container_score(parent)
        if score >= 0:
            if requires_datetime:
                if _has_datetime_in_ancestors(parent):
                    candidates.append((parent, depth, score))
            else:
                candidates.append((parent, depth, score))
        parent = parent.parent
        depth += 1

    if not candidates:
        return None, 0

    # 优先选择最高分的容器，分数相同时选最低深度
    candidates.sort(key=lambda x: (-x[2], x[1]))
    return candidates[0][0], candidates[0][1]


def _find_news_item_parent(a_tag, stop_at_container=None, max_depth=15) -> 'Tag | None':
    """
    找新闻链接所在的新闻项容器（li/div.item/div.box 等）。
    向上遍历最多 max_depth 层，返回找到的第一个匹配容器。

    优先找结构化标签（li/tr/article/section），找不到时再找有容器 class 名的 div。
    stop_at_container: 如果传入列表块容器，则不越过该容器（避免把整个列表块当作文档项容器）
    """
    # 第一轮：找结构化标签
    parent = a_tag.parent
    depth = 0
    hit_stop = False
    while parent and depth < max_depth:
        if stop_at_container is not None and parent is stop_at_container:
            hit_stop = True
            break
        if parent.name in ('li', 'tr', 'article', 'section'):
            return parent
        parent = parent.parent
        depth += 1

    # 第二轮：如果在 stop_at_container 处中断，从 a_tag.parent 向上检查每个祖先
    # 直到 stop_at_container，寻找有容器关键词的 div
    if hit_stop and stop_at_container is not None:
        parent = a_tag.parent
        depth = 0
        while parent and depth < max_depth:
            if parent is stop_at_container:
                break
            if parent.name == 'div':
                classes = parent.get('class') or []
                class_str = ' '.join(classes).lower()
                if any(kw in class_str for kw in _CONTAINER_KW):
                    return parent
            parent = parent.parent
            depth += 1
        return None
    else:
        # 未到达 stop_at_container，继续从断点找容器
        while parent and depth < max_depth:
            if parent.name == 'div':
                classes = parent.get('class') or []
                class_str = ' '.join(classes).lower()
                if any(kw in class_str for kw in _CONTAINER_KW):
                    return parent
            parent = parent.parent
            depth += 1

    return None


def _is_contained_in(inner: 'Tag', outer: 'Tag') -> bool:
    """检查 inner 是否在 outer 的子树中（inner 是 outer 的后代）"""
    parent = inner.parent
    while parent:
        if parent is outer:
            return True
        parent = parent.parent
    return False


def _find_list_blocks(soup: BeautifulSoup) -> list:
    """
    找到顶级新闻列表容器（body 直系子元素中包含新闻链接的块），
    及其包含的新闻链接列表。
    返回 [(container_element, [a_tag, ...]), ...]，按 DOM 顺序排列。

    如果某个子元素本身包含新闻链接，但其父元素也是列表块容器，
    则该子元素是子列表块（应合并到父列表块中，而不是单独作为一个块）。
    """
    body = soup.find('body')
    if not body:
        return []

    # Step 1: 收集所有 body 直系子元素中包含新闻链接的块
    raw_blocks: list[tuple['Tag', list]] = []
    for child in body.children:
        if not hasattr(child, 'name') or not child.name:
            continue
        links = [a for a in child.find_all('a', href=True) if _is_news_link(a)]
        if links:
            raw_blocks.append((child, links))

    # Step 2: 排除被其他块包含的子块（嵌套列表块场景）
    top_blocks: list[tuple['Tag', list]] = []
    for candidate, candidate_links in raw_blocks:
        is_nested = False
        for parent_candidate, _ in raw_blocks:
            if candidate is parent_candidate:
                continue
            if _is_contained_in(candidate, parent_candidate):
                is_nested = True
                break
        if not is_nested:
            top_blocks.append((candidate, candidate_links))

    # Step 3: 对每个顶级块，收集其所有新闻链接（包括嵌套子块的）
    result: list[tuple['Tag', list]] = []
    for block_container, _ in top_blocks:
        all_links = [a for a in block_container.find_all('a', href=True) if _is_news_link(a)]
        result.append((block_container, all_links))

    return result


def _find_wrapper_in_container(a_tag: 'Tag', container: 'Tag', exclude: 'Tag | None = None') -> 'Tag | None':
    """
    当 a 标签没有中间新闻项容器时，在 container 内找 a 的最近非 a 标签祖先。
    适用于 <div.container > div.headlines_p > a 或 <ul > a 这样的情况。
    找到后返回该祖先元素（需要和 container 是直接子代关系），否则返回 None。

    exclude: 排除的标签（通常是当前处理的子块），避免将子块本身误认为 wrapper
    """
    parent = a_tag.parent
    while parent and parent is not container:
        if parent.name == 'a':
            parent = parent.parent
            continue
        if exclude is not None and parent is exclude:
            parent = parent.parent
            continue
        if parent.parent is container:
            return parent
        parent = parent.parent
    return None


def _get_sub_blocks(container: 'Tag') -> list:
    """
    找到 container 的直接子元素中，可以作为新闻项容器的元素。
    用于识别列表块内的子列表（如 div.headlines、div.focus 等）。
    """
    sub_blocks = []
    for child in container.children:
        if not hasattr(child, 'name') or not child.name:
            continue
        if child.name not in ('div', 'li', 'tr', 'article', 'section', 'ul'):
            continue
        links = [a for a in child.find_all('a', href=True) if _is_news_link(a)]
        if links:
            sub_blocks.append(child)
    return sub_blocks


def _truncate_single_block(
    sub_block: 'Tag',
    sub_block_links: list,
    keep_count: int,
    removed_targets: set,
) -> int:
    """
    对单个子块进行截断，保留前 keep_count 个新闻项（容器）。
    每个新闻项容器可能包含多个新闻链接，这些链接会被一起保留或移除。
    返回实际保留的新闻项数量。

    用于子块内没有全局保留链接时的递归处理。
    """
    if len(sub_block_links) <= keep_count:
        # 链接数不足 keep_count，全部保留，返回实际链接数
        return len(sub_block_links)

    # 按 DOM 顺序遍历子块链接，识别独立新闻项（容器）
    item_link_map: dict[int, list] = {}  # item_id -> list of links in it

    for a in sub_block_links:
        if not hasattr(a, 'attrs') or a.attrs is None:
            continue
        item = _find_news_item_parent(a, stop_at_container=sub_block)
        item_id = id(item) if item else None

        if item_id is None:
            # 没有容器的链接：视为独立项，按 DOM 顺序计入
            item_id = id(a)  # 用 a 自身的 id 作为唯一标识

        if item_id not in item_link_map:
            item_link_map[item_id] = []
        item_link_map[item_id].append(a)

    # 按首次出现顺序统计容器数，保留前 keep_count 个
    # 注意：只统计真正的新闻项容器（li/tr/article/section），跳过无容器的链接
    items_kept = 0
    items_to_remove: list[int] = []
    any_real_container_kept = False

    for item_id, links_in_item in item_link_map.items():
        # 检查是否是真正的新闻项容器
        first_a = links_in_item[0]
        item = _find_news_item_parent(first_a)
        is_real_container = item is not None and item.name in ('li', 'tr', 'article', 'section')

        if is_real_container:
            # 真正的新闻项容器，才计入 keep_count
            if items_kept < keep_count:
                items_kept += 1
                any_real_container_kept = True
            else:
                items_to_remove.append(item_id)
        # 非容器链接不计入 keep_count，也不标记移除（保留原样）

    # 如果只有 1 个容器且包含所有链接，无法按容器截断，
    # 回退为直接按链接截断（保留前 keep_count 个链接）
    # 注意：当没有真正的容器时（全是无容器的链接），也应该走 link-based 截断逻辑
    if len(items_to_remove) == 0 and (len(item_link_map) == 1 or not any_real_container_kept):
        to_keep = sub_block_links[:keep_count]
        keep_ids = {id(a) for a in to_keep if hasattr(a, 'attrs') and a.attrs}
        for a in sub_block_links:
            if id(a) not in keep_ids and id(a) not in removed_targets:
                a.decompose()
                removed_targets.add(id(a))
        # link-based 截断保留 keep_count 个
        return keep_count

    # 统一移除被标记的项（避免 decompose 过程中影响后续处理）
    for item_id in items_to_remove:
        links_in_item = item_link_map[item_id]
        for a in links_in_item:
            if id(a) not in removed_targets:
                # 找父容器（<li>），分解整个容器而不是只分解 <a>
                item = _find_news_item_parent(a)
                if item and item.name == 'li':
                    item.decompose()
                else:
                    a.decompose()
                removed_targets.add(id(a))

    # 返回实际保留的容器数
    return items_kept


def _truncate_block(container: 'Tag', links: list, keep_count: int) -> None:
    """
    对一个列表块截断到前 keep_count 个新闻项。
    直接在 container 上操作，移除多余新闻项的容器元素。

    策略：
    1. 列表容器（ul/ol）：直接子元素共享 keep_count 预算，按 DOM 顺序保留前 N 个
    2. 板块容器（div/section/article）：遍历所有直接子元素，
       每个子元素独立 keep_count 预算
    3. 叶子块（无嵌套结构）：在 container 内按 keep_count 截断链接
    """
    removed_targets: set[int] = set()
    is_list_container = container.name in ('ul', 'ol')

    if is_list_container:
        # 列表容器：直接子元素（li/tr/...）共享预算，按 DOM 顺序保留前 keep_count 个
        # 必须遍历全部子元素（含无 a 标签的时间/装饰项），否则孤立装饰项会残留导致 li 数超过 keep_count
        children = [c for c in container.children
                    if hasattr(c, 'name') and c.name and c.name in ('li', 'tr', 'article', 'section', 'div')]
        remaining = keep_count
        for child in children:
            if id(child) in removed_targets:
                continue
            if remaining <= 0:
                child.decompose()
                removed_targets.add(id(child))
                continue
            remaining -= 1
        return

    # 板块容器或叶子块
    sub_blocks = _get_sub_blocks(container)

    if not sub_blocks:
        # 叶子块：没有子块，在 container 内按 keep_count 截断
        links_to_keep = links[:keep_count]
        keep_hrefs = {a.get('href') or '' for a in links_to_keep
                      if a.get('href') and hasattr(a, 'attrs') and a.attrs}
        container_links = [a for a in container.find_all('a', href=True)
                           if _is_news_link(a) and hasattr(a, 'attrs') and a.attrs]
        for a in container_links:
            if not hasattr(a, 'attrs') or a.attrs is None:
                continue
            href = a.get('href') or ''
            if href not in keep_hrefs:
                item = _find_news_item_parent(a, stop_at_container=container)
                if item and id(item) not in removed_targets:
                    item.decompose()
                    removed_targets.add(id(item))
                else:
                    wrapper = _find_wrapper_in_container(a, container, exclude=None)
                    if wrapper and id(wrapper) not in removed_targets:
                        wrapper.decompose()
                        removed_targets.add(id(wrapper))
                    else:
                        a.decompose()
        return

    # 板块容器：遍历所有直接子元素（div/section/article/ul/ol），
    # 各自独立预算。注意：必须包含无新闻链接的子元素（如 div.bangdan_box），
    # 否则其内部的 ul 不会被截断。
    for child in container.children:
        if not hasattr(child, 'name') or not child.name:
            continue
        if child.name not in ('div', 'section', 'article', 'ul', 'ol'):
            continue
        if id(child) in removed_targets:
            continue

        # 检查是否有嵌套的 ul/ol 列表（真正的列表容器）
        # 方法：递归查找 ul/ol，直到找到为止
        # max_depth=30 以应对深度嵌套的 div 包裹结构（每层包装 div 都计数）
        def find_nested_uls(c, depth=0, max_depth=30):
            nested = []
            if depth >= max_depth:
                return nested
            for ch in c.children:
                if not hasattr(ch, 'name') or not ch.name:
                    continue
                if ch.name in ('ul', 'ol'):
                    nested.append(ch)
                else:
                    nested.extend(find_nested_uls(ch, depth + 1, max_depth))
            return nested

        nested_uls = find_nested_uls(child)

        if child.name in ('ul', 'ol'):
            # 子元素本身就是 ul/ol：按列表容器逻辑截断（迭代全部 li，含无 a 的孤立项）
            _truncate_block(child, [], keep_count)
        elif nested_uls:
            # 子元素是 div，内部嵌套了 ul/ol
            for ul in nested_uls:
                _truncate_block(ul, [], keep_count)
        else:
            # 无嵌套列表：作为叶子块处理
            child_links = [a for a in child.find_all('a', href=True)
                           if _is_news_link(a) and hasattr(a, 'attrs') and a.attrs]
            _truncate_single_block(child, child_links, keep_count, removed_targets)


def truncate_html_by_news_items(
    html: str,
    max_size: int,
    keep_count: int = DEFAULT_NEWS_BLOCK_COUNT,
) -> str:
    """
    截取 HTML：保留完整 DOM 结构，只保留前 N 个新闻块，其他新闻块整个移除。
    超出 max_size 时按完整标签安全截断。

    策略：
    1. 按顶级列表块（body 直系子元素）分组
    2. 每个块内各自保留前 keep_count 个新闻项
    """
    soup = BeautifulSoup(html, "html.parser")

    news_links = [a for a in soup.find_all("a", href=True) if _is_news_link(a)]
    if not news_links:
        return safe_truncate(html, max_size) if len(html) > max_size else html

    list_blocks = _find_list_blocks(soup)
    if not list_blocks:
        return safe_truncate(html, max_size) if len(html) > max_size else html

    for container, links in list_blocks:
        _truncate_block(container, links, keep_count)

    result = str(soup)

    if len(result) > max_size and max_size < 200 * 1024:
        result = safe_truncate(result, max_size)
    return result