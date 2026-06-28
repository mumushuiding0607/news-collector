"""
article.py - 文章正文 HTML 清洗
"""

from __future__ import annotations

import re
import html as html_module

from bs4 import BeautifulSoup

from ._constants import (
    _ATTR_REMOVE_LINKLESS_RE,
    DATE_REGEX,
    is_date_text,
    _ARTICLE_TITLE_RE,
    _TIME_CLASS_RE,
    _DETAIL_CONTENT_RE,
    _ARTICLE_CONTENT_RE,
    _CONTENT_CLASS_RE,
)


def clean_article_html(html: str, keep_metadata: bool = True) -> str:
    """
    清洗文章详情页 HTML（统一版）。

    策略：
    1. 移除 nav/header/footer/aside/style/script/noscript
    2. 找所有"正文候选"元素：含 >30 字文本节点的元素（通常是 <p>）
    3. 找正文候选的最小共同祖先 → 这就是正文容器
    4. 同时识别标题/时间元素（仅用于单独输出元信息）
    5. 清洗无用属性，移除链接属性

    这种"找包含多个 >30 字正文段的最小公共父容器"算法对以下结构都生效：
    - 标题/时间与正文在同一祖先（ic-ceca .index 包含 .caption + .yysf_time + <p>）
    - 标题/时间与正文在不同兄弟节点（chinania .article_title 与 .article_content 同属 .container.article）
    """
    soup = BeautifulSoup(html, 'html.parser')

    for tag in soup.find_all(['nav', 'header', 'footer', 'aside', 'style', 'script', 'noscript']):
        tag.decompose()

    from ._constants import DATE_REGEX

    # 找标题：h1-h6 且文本 > 10，或 class 包含 title 且文本 > 10
    title_elem = None
    for tag in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
        text = tag.get_text(strip=True)
        if len(text) > 10:
            title_elem = tag
            break
    if not title_elem:
        for tag in soup.find_all(class_=re.compile(r'title', re.I)):
            text = tag.get_text(strip=True)
            if len(text) > 10:
                title_elem = tag
                break

    # 找时间：包含日期和时间文本的元素（文本最短的优先）
    time_elem = None
    best_score = (-1, -float('inf'))
    for tag in soup.find_all(True):
        if tag.name in ['script', 'style', 'noscript', 'html', 'head']:
            continue
        text = tag.get_text(strip=True)
        if text and DATE_REGEX.search(text):
            has_date_and_time = bool(re.search(r'\d{4}[年/-]\d{2}[月/-]\d{2}[日]?\s+\d{2}:\d{2}', text))
            score = (1 if has_date_and_time else 0, -len(text))
            if score > best_score:
                best_score = score
                time_elem = tag

    # 核心：找所有"正文候选"元素（直接含 >30 字文本的 <p>）
    # 这是新算法：找包含多个正文段的最小公共父容器
    # 只考虑 <p>，不混入 <div>：div 可能是布局容器（breadcrumb/sidebar/tab 文本），
    # 会被误当成"正文段"拉高最小共同祖先。
    body_candidates = []
    for tag in soup.find_all('p'):
        # 排除位于 footer/header/sidebar/audio/control 等噪声区域的元素
        # 否则这些区域的 p 会把"最小共同祖先"向上推到 main/div 顶层，
        # 让 LLM 拿不到真正的正文容器 selector（如 rm_txt_con）。
        if _is_inside_noise_section(tag):
            continue
        own_text = ''.join(
            str(c) for c in tag.children if isinstance(c, str)
        ).strip()
        if len(own_text) > 30:
            body_candidates.append(tag)

    # 找 body_candidates 的最小共同祖先
    content = None
    if body_candidates:
        # 计算所有 body_candidates 的祖先链交集
        common_ancestors = None
        for elem in body_candidates:
            elem_ancestors = set()
            parent = elem
            while parent:
                elem_ancestors.add(id(parent))
                parent = parent.parent
            if common_ancestors is None:
                common_ancestors = elem_ancestors
            else:
                common_ancestors &= elem_ancestors
        # 在共同祖先中找最小的，优先选"含非 candidate 子元素"的容器
        # 例：people.com.cn 结构是
        #   div.col-1 > div.rm_txt_con.cf > div.bread + div#rm_txt_zw + ... + p*4
        # 最小共同祖先是 div#rm_txt_zw（只含 p），但 div.rm_txt_con.cf 含 bread 等
        # 非 candidate 子元素，是真正的"文章容器"。优先选它可保留 rm_txt_con cf
        # 这种容器类名供 LLM 学习。
        if common_ancestors:
            with_siblings = []   # (text_len, tag) 含非 candidate 子元素的祖先
            default = []         # (text_len, tag) 所有候选
            candidate_ids = {id(c) for c in body_candidates}
            for tag in soup.find_all(True):
                if id(tag) in common_ancestors:
                    text_len = len(tag.get_text())
                    default.append((text_len, tag))
                    # 排除 candidate 本身，看是否有其他带文本的元素子节点
                    child_tags = [c for c in tag.children if hasattr(c, 'name') and c.name]
                    has_non_candidate = any(
                        id(c) not in candidate_ids and c.get_text(strip=True)
                        for c in child_tags
                    )
                    if has_non_candidate:
                        with_siblings.append((text_len, tag))
            if with_siblings:
                with_siblings.sort(key=lambda x: x[0])
                content = with_siblings[0][1]
            elif default:
                default.sort(key=lambda x: x[0])
                content = default[0][1]

        # 单候选时：算法可能选中 candidate 本身（<p>），其祖先更可能是正文容器
        # （如 people.com.cn 的 div#rm_txt_zw）。提升到第一个有 id 或 class 的祖先。
        if len(body_candidates) == 1 and content is body_candidates[0]:
            current = content.parent
            while current and current.name:
                if current.get('id') or current.get('class'):
                    content = current
                    break
                current = current.parent

    # 兜底：若没找到正文候选，用 title+time 共同祖先（兼容极短快讯/无正文的页面）
    if not content and title_elem and time_elem:
        title_ancestors = set()
        parent = title_elem
        while parent:
            title_ancestors.add(id(parent))
            parent = parent.parent
        time_ancestors = set()
        parent = time_elem
        while parent:
            time_ancestors.add(id(parent))
            parent = parent.parent
        common_ancestors = title_ancestors & time_ancestors

        def normalize_text(t: str) -> str:
            return re.sub(r'\s+', ' ', t)
        title_text_norm = normalize_text(title_elem.get_text())
        time_text_norm = normalize_text(time_elem.get_text())
        for ancestor_id in common_ancestors:
            for tag in soup.find_all(True):
                if id(tag) == ancestor_id:
                    tag_text_norm = normalize_text(tag.get_text())
                    if title_text_norm in tag_text_norm and time_text_norm in tag_text_norm:
                        if content is None or len(tag.get_text()) < len(content.get_text()):
                            content = tag
                    break

    if not content:
        cleaned = _extract_long_text_elements(html)
        return f'<!DOCTYPE html><html><head></head><body>{cleaned}</body></html>'

    # 对 content 剪枝：移除短文本（<30字且非日期）元素
    content_soup = BeautifulSoup(str(content), 'html.parser')
    _prune_soup(content_soup, min_text_length=30)
    content_str = str(content_soup)

    # 组装结果：只输出不在 content 内的 standalone 元素
    parts = []

    if title_elem is not None and title_elem not in content.descendants:
        parts.append(str(title_elem))

    if time_elem is not None and time_elem not in content.descendants:
        parts.append(str(time_elem))

    parts.append(content_str)

    combined = '\n'.join(parts)
    cleaned = _ATTR_REMOVE_LINKLESS_RE.sub('', combined)

    # unwrap <a> 标签：移除链接标记，只保留纯文本（避免 get_text 时产生换行）
    # 匹配 <a href="...">文字</a> 或 <a class="..." href="...">文字</a> 等
    # 不匹配空链接 <a href="..."></a>
    cleaned = re.sub(r'<a[^>]*>([^<]+)</a>', r'\1', cleaned)

    return f'<!DOCTYPE html><html><head></head><body>{cleaned}</body></html>'


def _prune_soup(soup: BeautifulSoup, min_text_length: int) -> None:
    """
    对已剥离 nav/header/footer/aside/script/noscript 的 BeautifulSoup 进行剪枝。

    两阶段处理：
    1. unwrap：把"无 own_text 且无有用属性"的纯包裹元素（div/span）解包，保留子元素
    2. prune：移除 own_text < min_text_length 且非日期的元素（连同后代）

    保留：h1-h6、有用属性的元素（class 含 content/detail/title/date 等）、长文本、日期。
    """
    # 阶段 1: unwrap 纯包裹元素
    _unwrap_pure_wrappers(soup)

    # 阶段 2: 移除短文本元素
    def get_direct_text(tag) -> str:
        texts = [str(c) for c in tag.children if isinstance(c, str)]
        return ''.join(texts).strip()

    def is_useful(tag) -> bool:
        if tag.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            return True
        txt = get_direct_text(tag)
        if len(txt) >= min_text_length:
            return True
        if is_date_text(txt):
            return True
        # <a> 标签内的文本（如股票名称+代码）通常很短（<30字），
        # 但不应被剪枝——后续 _ATTR_REMOVE_LINKLESS_RE 会移除 href 属性，
        # 保留纯文本。空链接（无文本）跳过，不保留。
        if tag.name == 'a' and txt:
            return True
        return False

    def has_useful_descendant(tag) -> bool:
        for child in tag.children:
            if child.name:
                if is_useful(child):
                    return True
                if has_useful_descendant(child):
                    return True
        return False

    for _ in range(2):
        to_remove = []
        for tag in soup.find_all(True):
            if tag.name in ['html', 'head', 'body']:
                continue
            if is_useful(tag):
                continue
            if has_useful_descendant(tag):
                continue
            txt = get_direct_text(tag)
            if len(txt) < min_text_length:
                to_remove.append(tag)
        for tag in to_remove:
            tag.decompose()


# 有信息价值的 class/id 关键词（保留这些元素的包裹作用）
# 故意只匹配"开发者显式命名"的容器，避免被 `newsItemTitleBind_Style1` 之类
# 模板自动生成的 class 名误导
_KEEP_CLASS_KW = re.compile(
    r'\b(content|detail|article|body|main|content_body|news_body|article-content|news-content|article_detail|article_detail_content|news-detail|article-detail|w-content|w-detail|w-title|w-body|w-article|w-news)\b',
    re.IGNORECASE,
)

# 噪声区域 class/id 关键词（其内部的 p/div 不作为正文候选）
# 这些是 layout/control/auxiliary 区段，里面的 p 文本（联系方式、版权、播放器说明等）
# 会污染"最小共同祖先"算法，让 LLM 学错正文容器。
# 不用 \b 边界（_ 是 word char 会阻止 rm_nav/header_bar 匹配），改用更宽松的边界
# （前后是非字母数字），兼顾驼峰（rmNav）和下划线（rm_nav）。
_NOISE_SECTION_KW = re.compile(
    r'(?:^|[^a-z0-9])(footer|header|nav|sidebar|aside|breadcrumb|crumb|menu|toolbar|'
    r'voice|audio|player|control|share|advert|promot|recommend|related|'
    r'comment|copyright|partner|trending|hot|rank)(?:$|[^a-z0-9])',
    re.IGNORECASE,
)


def _is_inside_noise_section(tag) -> bool:
    """判断 tag 是否位于 footer/header/sidebar/control 等噪声区域（祖先 class/id 命中噪声关键词）"""
    for ancestor in tag.find_parents():
        if not ancestor.get('class') and not ancestor.get('id'):
            continue
        for attr_val in list(ancestor.get('class') or []) + [ancestor.get('id') or '']:
            if attr_val and _NOISE_SECTION_KW.search(attr_val):
                return True
    return False


def _has_informative_attrs(tag) -> bool:
    """判断元素是否有信息价值的属性（class/id 含 content/detail/article 等关键词）"""
    for attr_val in tag.attrs.values():
        if isinstance(attr_val, list):
            for v in attr_val:
                if isinstance(v, str) and _KEEP_CLASS_KW.search(v):
                    return True
        elif isinstance(attr_val, str) and _KEEP_CLASS_KW.search(attr_val):
            return True
    return False


def _unwrap_pure_wrappers(soup: BeautifulSoup) -> None:
    """
    把"无 own_text 且无信息价值属性"的纯包裹 div/span 解包（保留子元素、移除标签本身）。

    解决模板页多层嵌套 div（如 smAreaC > esmartMargin > yibuFrameContent > ...）包裹问题。

    例外：根容器不参与解包——
    - body 的直接子元素（全文 soup 中算法识别出的正文根容器）
    - [document] 的直接子元素（str(content) 重新解析后的单根内容，
      html.parser 不会自动加 body）
    否则 LLM 会丢失"这是正文容器"的语义线索（如 rm_txt_con cf），
    只能退而选布局类名（col-1-1）这种 div，导致学错 selector。
    """
    # 多次迭代，处理嵌套包裹（外层 unwrap 后内层会变成直接子元素，可继续 unwrap）
    for _ in range(10):
        changed = False
        to_unwrap = []
        for tag in soup.find_all(['div', 'span']):
            if tag.name in ['html', 'head', 'body']:
                continue
            # 跳过根容器：
            # - body 的直接子元素（=全文 soup 中算法识别出的正文根容器）
            # - [document] 的直接子元素（=str(content) 重新解析后的单根内容，
            #   html.parser 不会自动加 body，没有 body 时退而检查 [document]）
            # 跳过根容器可以保留正文容器的 class 线索（如 rm_txt_con），
            # 否则 LLM 会丢失"这是正文容器"的语义，只能退而选布局类名（col-1-1）。
            if tag.parent and tag.parent.name in ('body', '[document]'):
                continue
            # 有 own_text 跳过
            own_text = ''.join(str(c) for c in tag.children if isinstance(c, str)).strip()
            if own_text:
                continue
            # 有信息价值 class/id 跳过
            if _has_informative_attrs(tag):
                continue
            to_unwrap.append(tag)
        for tag in to_unwrap:
            tag.unwrap()
            changed = True
        if not changed:
            break


def _extract_long_text_elements(html: str, min_text_length: int = 30) -> str:
    """提取包含长文本或日期的元素（保留 DOM 结构）。"""
    soup = BeautifulSoup(html, 'html.parser')

    for tag in soup.find_all(['nav', 'header', 'footer', 'aside', 'style', 'script', 'noscript']):
        tag.decompose()

    _prune_soup(soup, min_text_length)

    body = soup.find('body')
    content = ''.join(str(c) for c in (body.children if body else soup.children)
                      if isinstance(c, str) or c.name)

    content = _ATTR_REMOVE_LINKLESS_RE.sub('', content)

    return content