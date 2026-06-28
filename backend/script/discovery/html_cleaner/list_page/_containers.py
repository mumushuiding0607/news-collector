# _containers.py - 列表容器提取
#
# 在清洗后的 HTML 中识别新闻列表容器，返回最小且完整的容器 HTML 列表。

from bs4 import BeautifulSoup
import re

from .._constants import NEWS_URL_REGEX
from script.common.datetimeutil import DATETIME_REGEX

# 完全无用的非文本元素
_NON_TEXT_TAGS = {'img', 'svg', 'canvas', 'audio', 'video', 'iframe', 'source', 'track'}

# 中文字符范围
_CHINESE_RE = re.compile(r'[一-鿿]')


def _get_title_text(a_tag) -> str:
    """获取 <a> 标签中的主要标题文本（取最长段落）"""
    all_texts = []
    for element in a_tag.find_all(True):
        text = element.get_text(strip=True)
        if text and len(text) >= 5:
            all_texts.append(text)
    if not all_texts:
        return a_tag.get_text(strip=True)
    return max(all_texts, key=len)


def _count_news_links(element) -> int:
    """统计元素中新闻链接的数量"""
    count = 0
    for a in element.find_all('a', href=True):
        if NEWS_URL_REGEX.search(a.get('href', '')):
            count += 1
    return count


def _has_news_link_and_time(element) -> bool:
    """检查元素是否同时包含新闻链接和时间元素"""
    for a in element.find_all('a', href=True):
        if NEWS_URL_REGEX.search(a.get('href', '')):
            return _contains_datetime_text(element)
    return False


def _contains_datetime_text(element) -> bool:
    """检查元素文本是否包含日期或时间"""
    from script.common.datetimeutil import DATETIME_REGEX
    text = element.get_text()
    return bool(DATETIME_REGEX.search(text)) if text else False


def _get_all_descendants_str(element) -> set:
    """获取元素所有后代的字符串表示，用于去重"""
    result = set()
    for child in element.descendants:
        if hasattr(child, 'name') and child.name:
            result.add(str(child))
    return result


# 通用框架层 id，不应作为列表容器
_GENERIC_IDS = {'__next', '__NEXT_DATA__', '__next-route-announcer__', '__tag-manager'}


def _has_id(element) -> bool:
    """检查元素是否有非通用框架的 id 属性"""
    return element.has_attr('id') and element.get('id') not in _GENERIC_IDS


def _get_ancestors(element) -> list:
    """获取元素的所有祖先元素列表"""
    ancestors = []
    parent = element.parent
    while parent:
        ancestors.append(parent)
        parent = parent.parent
    return ancestors


def _prune_container(soup: BeautifulSoup) -> None:
    """
    对容器内部进行剪枝，移除空结构元素。
    移除条件：自身无新闻链接 + 无日期时间 + 无实质文本 + 无有意义的子元素
    """
    # 非文本元素：直接移除
    for tag in soup.find_all(_NON_TEXT_TAGS):
        tag.decompose()

    # 空结构元素：逐层向上检查，移除无意义的包装器
    changed = True
    root = soup.find(True)  # 获取根元素，不移除根元素本身
    while changed:
        changed = False
        for tag in soup.find_all():
            if not hasattr(tag, 'children') or tag.name in _NON_TEXT_TAGS:
                continue
            if tag is root:
                continue  # 不移除根元素
            if _is_prunable_element(tag):
                tag.decompose()
                changed = True
                break


def _is_prunable_element(tag) -> bool:
    """
    判断容器内的元素是否可移除（剪枝条件）。
    满足任一保留条件则不移除：
    - 包含新闻链接
    - 文本是日期/时间格式
    - 属性值含日期
    - 中文字符数 >= 3（实质性短文本，如"推荐"等）
    - 有有意义的子元素
    """
    # 非 Tag 对象（文本节点等）直接可移除
    if not hasattr(tag, 'name') or not tag.name:
        return True
    if tag.name in _NON_TEXT_TAGS:
        return True

    # 包含新闻链接 → 保留
    if _has_news_link(tag):
        return False

    # 文本含日期时间 → 保留
    text = tag.get_text(strip=True)
    if text and (DATETIME_REGEX.search(text) or _has_datetime_in_attrs(tag)):
        return False

    # 中文字符数 >= 10 → 保留（实质性文本）
    chinese_count = len(_CHINESE_RE.findall(text))
    if chinese_count >= 10:
        return False

    # 有有意义的子元素 → 保留
    for child in tag.children:
        if not hasattr(child, 'name') or child.name in ['\n', '\r', '\t']:
            continue
        if not _is_prunable_element(child):
            return False

    # 所有条件都不满足 → 可移除
    return True


def _has_news_link(tag) -> bool:
    """元素内是否包含新闻链接"""
    for a in tag.find_all('a', href=True):
        if NEWS_URL_REGEX.search(a.get('href', '')):
            return True
    return False


def _has_datetime_in_attrs(tag) -> bool:
    """属性值中是否包含日期/时间"""
    for attr_values in tag.attrs.values():
        if isinstance(attr_values, list):
            for av in attr_values:
                if DATETIME_REGEX.search(str(av)):
                    return True
        elif isinstance(attr_values, str):
            if DATETIME_REGEX.search(attr_values):
                return True
    return False


# 纯粹的布局类 class 前缀（不含具体业务标识），用于过滤通用包装器
# 注意：wrapper-left-content / wrapper-right-content 是业务 list 容器，不是布局包装器
_LAYOUT_CLASS_PREFIXES = (
    'wrapper-content', 'layout_content', 'clearfix', 'layout_', 'section_', 'main_', 'header_', 'footer_',
    'container-', 'content-wrap', 'contentWrapper', 'layoutWrapper',
)


def _is_pure_layout_class_element(element) -> bool:
    """
    检查元素是否只有纯粹的布局类 class（无具体业务标识）。
    只有 class 名称匹配布局前缀（且不包含业务特征词）的才认为是布局容器。
    """
    classes = element.get('class') or []
    for c in classes:
        c_lower = c.lower()
        # 检查是否匹配布局前缀
        matched = any(c_lower.startswith(p.lower()) or c_lower == p.lower() for p in _LAYOUT_CLASS_PREFIXES)
        if matched:
            return True
    return False


def _build_container_candidate(parent, link_count: int) -> tuple:
    """
    构建容器候选元组，用于排序。
    返回 (-link_count, has_id, parent, container_str)
    链接数多的在前（降序），有 id 优先
    """
    container_str = str(parent)
    has_id = 1 if _has_id(parent) else 0
    return (-link_count, has_id, parent, container_str)


def extract_news_containers(html: str) -> list[str]:
    """
    用 BeautifulSoup 提取新闻列表区块 HTML。

    策略：
    1. 找列表容器——包含多个新闻链接的最小容器，优先使用 id 定位
    2. 找新闻项容器——恰好包含 1 个链接 + 时间元素的容器
    3. 使用字符串去重，同一个容器只保留一次
    """
    soup = BeautifulSoup(html, 'html.parser')
    container_htmls = []
    seen = set()

    # Step 1: 收集所有符合条件的新闻链接 <a> 标签
    a_tags = []
    for a_tag in soup.find_all('a', href=True):
        if not NEWS_URL_REGEX.search(a_tag.get('href', '')):
            continue
        # 链接文本>=10字符，或直接父元素文本>=10（有些页面锚文本为空但父容器有文本）
        title_text = _get_title_text(a_tag)
        if len(title_text) >= 10:
            a_tags.append(a_tag)
            continue
        # 备选：父元素文本>=10
        parent_text = a_tag.parent.get_text(strip=True) if a_tag.parent else ''
        if len(parent_text) >= 10:
            a_tags.append(a_tag)

    if not a_tags:
        return container_htmls

    # Step 2: 找列表容器（包含多个新闻链接的容器）
    # 收集所有包含2+新闻链接的容器，优先保留带 id 的容器
    all_containers = []
    for a_tag in a_tags:
        parent = a_tag.parent
        while parent:
            if parent.name in ('ul', 'ol', 'div', 'td', 'tr', 'tbody', 'table'):
                link_count = _count_news_links(parent)
                if link_count >= 2:
                    candidate = _build_container_candidate(parent, link_count)
                    all_containers.append(candidate)
                parent = parent.parent
            else:
                parent = parent.parent

    if all_containers:
        # 按链接数多的在前（降序）；外层 class 容器优先，相同链接数时 id 容器排后
        all_containers.sort(key=lambda x: (x[0], 1 if x[1] else 0))
        # 去重：保留有唯一标识的容器，跳过子容器和包装器
        kept_elements = []  # [(element, link_count)]
        for link_count, has_id, element, container_str in all_containers:
            if container_str in seen:
                continue
            # 跳过 body/html 等结构元素
            if element.name in ('body', 'html'):
                continue
            # 跳过无标识的结构性 div（无 id、无 class、不是 ul/ol）
            elem_id = element.get('id', '')
            elem_class = element.get('class') or []
            if not elem_id and not elem_class and element.name not in ('ul', 'ol'):
                continue
            # 跳过纯粹布局类容器（如 wrapper-content、layout_contentWarp 等）
            if elem_class and _is_pure_layout_class_element(element):
                continue
            # 跳过通用框架 id 的元素
            if elem_id in _GENERIC_IDS:
                continue
            # 如果当前元素是某个已保留容器的后代（当前元素是内层子容器），跳过
            if any(element in kept_elem.descendants for kept_elem, _ in kept_elements):
                continue
            # 对容器内部进行二次剪枝，移除空结构元素
            container_soup = BeautifulSoup(container_str, 'html.parser')
            _prune_container(container_soup)
            pruned_str = str(container_soup)
            container_htmls.append(pruned_str)
            kept_elements.append((element, -link_count))
            seen.add(container_str)
    else:
        # Step 3: 没找到列表容器（2+链接）→ 找新闻项容器
        # 宽松条件：接受任意 link_count >= 1，跳过 datetime 强制要求
        for a_tag in a_tags:
            news_item_container = None
            parent = a_tag
            while parent:
                if parent.name in ['ul', 'ol', 'div', 'td', 'tr', 'tbody', 'table']:
                    link_count = _count_news_links(parent)
                    if link_count >= 1:
                        news_item_container = parent
                        break
                parent = parent.parent

            if not news_item_container:
                news_item_container = a_tag.parent

            if not news_item_container or not hasattr(news_item_container, 'name'):
                continue

            container_str = str(news_item_container)
            if container_str not in seen:
                seen.add(container_str)
                container_htmls.append(container_str)
            for d in _get_all_descendants_str(news_item_container):
                seen.add(d)

    return container_htmls
