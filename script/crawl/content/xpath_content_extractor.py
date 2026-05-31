"""
xpath_content_extractor.py - 基于 lxml + XPath 的精准正文提取模块

与原有的 content_filter.py 形成 A/B 对比测试。
"""
import re
from typing import Optional
from lxml.html import HtmlElement, fromstring

NOISE_TAGS = set(["script", "style", "noscript", "iframe"])
NOISE_KEYWORDS = [
    "nav", "navigation", "menu",
    "footer", "foot", "bottom",
    "header", "head", "topbar", "top-bar",
    "aside", "sidebar", "side-bar", "right-bar",
    "comment", "comments", "comment-list",
    "social", "share", "sharing", "share-btn",
    "ad", "ads", "advert", "advertisement", "promo", "banner",
    "breadcrumb", "crumbs", "location",
    "pagination", "pager", "page-nav",
    "related", "recommend", "hot-topic",
    "widget", "widgets", "tool",
    "login", "signin", "signup", "register", "auth",
    "search", "searchbox", "search-form",
    "logo", "brand", "branding",
    "copyright", "sitemap", "friend-link",
    "subscribe", "newsletter", "email",
    "qrcode", "qr-code", "wechat", "weixin", "weibo",
    "video", "audio", "player", "media",
    "download", "app", "mobile",
    "tag", "tags", "label",
    "author", "writer", "about-author",
]

def _get_tag_name(elem) -> str:
    """安全获取元素标签名"""
    try:
        tag = getattr(elem, 'tag', None)
        if tag is None:
            return ""
        if isinstance(tag, str):
            return tag.lower()
        # 处理特殊对象（如 cython 包装的对象）
        return str(tag).lower()
    except Exception:
        return ""

CONTENT_KEYWORDS = ["article", "main", "post", "entry", "text", "content", "article-content", "news-content"]
TAG_WEIGHTS = {"article": 1.5, "main": 1.4, "section": 1.2, "div": 1.0, "p": 1.1}
XPATH_SELECTORS = [
    # 快科技：main_box 是文章主容器
    "//div[contains(@class, 'main_box')]",
    # 人民网
    "//div[contains(@class, 'rm_txt')]//div[contains(@class, 'col-1')]",
    "//div[contains(@class, 'rm_txt')]",
    "//div[contains(@class, 'rm_txt_con')]",
    # 农业农村部等 CMS
    "//div[contains(@class, 'TRS_Editor')]",
    # 通用选择器
    "//div[contains(@class, 'article-content')]",
    "//div[contains(@class, 'news-content')]",
    "//div[contains(@class, 'news_text')]",
    "//div[contains(@class, 'content')]",
    # 语义标签
    "//article",
    "//article[contains(@class, 'content')]",
    "//article[contains(@class, 'article')]",
    "//main",
    "//main[contains(@class, 'content')]",
    # 通用 div
    "//div[contains(@class, 'article')]",
    "//div[contains(@class, 'post')]",
    "//div[contains(@class, 'text')]",
    "//div[contains(@class, 'entry')]",
    "//div[contains(@class, 'detail')]",
    "//section[contains(@class, 'content')]",
    "//section[contains(@class, 'article')]",
    "//div[@class='content']",
    "//div[@id='content']",
]

def remove_noise_elements(root):
    for tag in NOISE_TAGS:
        for elem in root.xpath(f".//{tag}"):
            p = elem.getparent()
            if p is not None: p.remove(elem)
    return root

def is_noise_block(elem):
    cid = (str(elem.get("class", "") or "") + " " + str(elem.get("id", "") or "")).lower()
    return any(kw in cid for kw in NOISE_KEYWORDS)

def calculate_text_density(elem):
    all_t = re.sub(r"\s+", "", " ".join(elem.xpath(".//text()")).strip())
    link_t = re.sub(r"\s+", "", " ".join(elem.xpath(".//a//text()")).strip())
    return len(all_t) / (len(link_t) + 1)

def get_element_score(elem):
    tag_name = _get_tag_name(elem)
    if not tag_name:
        return 0.0

    tw = TAG_WEIGHTS.get(tag_name, 0.8)
    ds = min(1.0, calculate_text_density(elem) / 100)
    text = " ".join(elem.xpath(".//text()")).strip()
    tl = len(re.sub(r"\s+", "", text))
    ls = 0.2 if tl < 50 else (0.5 if tl < 200 else (0.8 if tl < 1000 else 1.0))
    pc = len([p for p in elem.xpath(".//p") if len("".join(p.xpath(".//text()"))) > 20])
    ps = min(1.0, pc / 3)
    cid = (str(elem.get("class") or "") + " " + str(elem.get("id") or "")).lower()
    kb = 0.2 if any(k in cid for k in CONTENT_KEYWORDS) else 0.0
    return min(1.0, tw * 0.2 + ds * 0.25 + ls * 0.25 + ps * 0.2 + kb)
    return min(1.0, tw * 0.2 + ds * 0.25 + ls * 0.25 + ps * 0.2 + kb)

def extract_text_from_element(elem):
    """从 lxml 元素中提取纯文本，保留段落结构"""
    parts = []

    # 获取元素的直接文本内容（.text）
    if elem.text and elem.text.strip():
        parts.append(elem.text.strip())

    # 遍历所有子元素
    for child in elem:
        if isinstance(child, str):
            # 这是尾随文本节点
            if child.strip():
                parts.append(child.strip())
        else:
            tag = _get_tag_name(child)

            # 递归获取子元素文本
            st = extract_text_from_element(child)
            if st.strip():
                # 根据标签类型决定是否换行
                if tag in ("p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "li"):
                    parts.append("\n" + st)
                else:
                    parts.append(" " + st if st else "")

    text = "".join(parts)
    # 清理多余空格和换行
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    # 清理残留的 HTML 标签
    text = re.sub(r"<[^>]+>", "", text)

    return text.strip()

def clean_boilerplate_text(text):
    """通用 Boilerplate 清理"""
    if not text:
        return text

    # 通用噪音模式
    patterns = [
        (r"^责任编辑：.*$", re.MULTILINE),
        (r"^责编：.*$", re.MULTILINE),
        (r"^编辑：.*$", re.MULTILINE),
        (r"^作者：.*$", re.MULTILINE),
        (r"^本文结束.*$", re.MULTILINE),
        (r"^如需转载.*$", re.MULTILINE),
        (r"^热门排行.*$", re.MULTILINE),
        (r"^热门推荐.*$", re.MULTILINE),
        (r"^相关推荐.*$", re.MULTILINE),
        (r"^推荐阅读.*$", re.MULTILINE),
        (r"^上一篇\s*$", re.MULTILINE),
        (r"^下一篇\s*$", re.MULTILINE),
        (r"^关注公众号.*$", re.MULTILINE),
        (r"^分享.*$", re.MULTILINE),
        (r"^微信扫一扫.*$", re.MULTILINE),
        (r"^【广告】.*$", re.MULTILINE),
        (r"^[|\-=]{3,}$", re.MULTILINE),
        (r"^©.*版权.*$", re.MULTILINE | re.IGNORECASE),
    ]

    for p, f in patterns:
        text = re.sub(p, "", text, flags=f)

    # 过滤空行
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()

def parse_html(html):
    if not html or not html.strip(): return None
    try: return remove_noise_elements(fromstring(html))
    except: return None

def _apply_xpath_selector(root, xpath):
    try: return root.xpath(xpath)
    except: return []

def extract_by_xpath(html, source_name=""):
    root = parse_html(html)
    if root is None: return ""

    candidates = []  # 收集所有有效候选

    for xp in XPATH_SELECTORS:
        for cand in _apply_xpath_selector(root, xp):
            if not isinstance(cand, HtmlElement) or is_noise_block(cand):
                continue
            s = get_element_score(cand)
            t = extract_text_from_element(cand)
            tl = len(re.sub(r"\s+", "", t))

            if tl >= 100:
                candidates.append((s, tl, t, xp))

    # 如果没有候选，遍历所有 div/article/section
    if not candidates:
        for block in root.xpath(".//div[@class] | .//article | .//section"):
            if not isinstance(block, HtmlElement) or is_noise_block(block):
                continue
            s = get_element_score(block)
            t = extract_text_from_element(block)
            tl = len(re.sub(r"\s+", "", t))
            if tl >= 100:
                candidates.append((s, tl, t, "fallback"))

    if not candidates:
        return ""

    # 排序：首先按文本量降序（优先提取更多信息），文本量相同则按分数降序
    candidates.sort(key=lambda x: (-x[1], -x[0]))

    # 返回文本量最大的结果
    return clean_boilerplate_text(candidates[0][2])

def extract_with_source_config(html, source_name):
    from pathlib import Path
    import json

    sources_path = Path(__file__).parent.parent.parent / "config" / "sources.json"

    if not sources_path.exists():
        return ""

    try:
        sources_data = json.loads(sources_path.read_text(encoding="utf-8"))

        for src in sources_data.get("sources", []):
            if src.get("name") == source_name:
                ce = src.get("contentExtract", "")

                if not ce:
                    return ""

                # 将正则 pattern 转换为更精确的 XPath
                # 例如: <div class="rm_txt_con cf" → //div[contains(@class, 'rm_txt_con')]
                ce_clean = ce.replace("(", "").replace(")", "")

                # 尝试从 contentExtract 提取 class 名称
                class_match = re.search(r'class="([^"]+)"', ce)
                if class_match:
                    first_word = class_match.group(1).split()[0]
                    # 构造精确的 XPath（确保括号闭合）
                    xpath = f"//div[contains(@class, '{first_word}')]"
                    root = parse_html(html)
                    if root is not None:
                        candidates = []
                        for cand in _apply_xpath_selector(root, xpath):
                            if isinstance(cand, HtmlElement) and not is_noise_block(cand):
                                t = extract_text_from_element(cand)
                                tl = len(re.sub(r"\s+", "", t))
                                if tl >= 100:
                                    candidates.append((tl, t))

                        if candidates:
                            # 按文本量降序排序
                            candidates.sort(key=lambda x: -x[0])
                            return clean_boilerplate_text(candidates[0][1])

                # 兜底：使用正则直接提取
                m = re.search(r'<([a-z]+)', ce, re.I)
                if m:
                    tag = m.group(1)
                    root = parse_html(html)
                    if root:
                        # 使用更精确的 XPath（避免 //div 这种太宽泛的选择器）
                        # 尝试匹配 class 包含 rm 或 txt 的 div
                        for xpath in [
                            f"//{tag}[contains(@class, 'rm_txt')]",
                            f"//{tag}[contains(@class, 'rm')]",
                            f"//{tag}[contains(@class, 'txt')]",
                            f"//{tag}[contains(@class, 'content')]",
                        ]:
                            candidates = []
                            for cand in _apply_xpath_selector(root, xpath):
                                if isinstance(cand, HtmlElement) and not is_noise_block(cand):
                                    t = extract_text_from_element(cand)
                                    tl = len(re.sub(r"\s+", "", t))
                                    if tl >= 100:
                                        candidates.append((tl, t))

                            if candidates:
                                candidates.sort(key=lambda x: -x[0])
                                return clean_boilerplate_text(candidates[0][1])

    except Exception:
        pass

    return ""

def extract_content_with_fallback(html, source_name=""):
    # 优先尝试数据源特定配置
    if source_name:
        c = extract_with_source_config(html, source_name)
        # 只有当结果文本量足够大时才使用（至少 500 字符）
        if c and len(c) >= 500:
            return c

    # 使用通用 XPath 提取
    c = extract_by_xpath(html, source_name)
    if c and len(c) >= 100:
        return c

    # 最后兜底：提取所有文本
    root = parse_html(html)
    if root is not None:
        all_t = re.sub(r"\s+", " ", " ".join([t.strip() for t in root.xpath(".//text()") if t.strip()])).strip()
        if len(all_t) >= 100:
            return clean_boilerplate_text(all_t)

    return ""

def extract_by_xpath_with_debug(html, source_name=""):
    result = {"content": "", "content_length": 0, "method": "none", "score": 0.0, "attempts": []}
    root = parse_html(html)
    if root is None: return result

    # 收集所有候选
    candidates = []
    for xp in XPATH_SELECTORS:
        for cand in _apply_xpath_selector(root, xp):
            if not isinstance(cand, HtmlElement) or is_noise_block(cand):
                continue
            s = get_element_score(cand)
            t = extract_text_from_element(cand)
            tl = len(re.sub(r"\s+", "", t))
            result["attempts"].append({"xpath": xp, "score": s, "length": tl, "success": tl >= 100})
            if tl >= 100:
                candidates.append((s, tl, t, xp))

    # 按文本量降序排序
    candidates.sort(key=lambda x: (-x[1], -x[0]))

    if candidates:
        result["score"] = candidates[0][0]
        result["content_length"] = candidates[0][1]
        result["content"] = clean_boilerplate_text(candidates[0][2])
        result["method"] = f"xpath:{candidates[0][3][:50]}"

    return result

if __name__ == "__main__":
    import sys
    from pathlib import Path
    if len(sys.argv) < 2:
        print("Usage: python xpath_content_extractor.py <html_file> [source_name]")
        sys.exit(1)
    html_path = Path(sys.argv[1])
    html_content = html_path.read_text(encoding="utf-8")
    source_name = sys.argv[2] if len(sys.argv) > 2 else ""
    print("=" * 60)
    print("XPath Content Extractor")
    print(f"Source: {source_name or 'unknown'}")
    print("=" * 60)
    content = extract_content_with_fallback(html_content, source_name)
    print(f"\nExtracted Content ({len(content)} chars):")
    print("-" * 60)
    print(content[:500] if content else "(empty)")
    debug_info = extract_by_xpath_with_debug(html_content, source_name)
    print(f"\nDebug: method={debug_info['method']}, score={debug_info['score']:.3f}")
    successful = [a for a in debug_info['attempts'] if a['success']]
    print(f"Successful: {len(successful)}/{len(debug_info['attempts'])}")
