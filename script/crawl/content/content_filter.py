"""
统一内容过滤器模块
封装 crawl4ai 内置的 PruningContentFilter，为所有数据源提供通用的文章正文过滤能力。

算法思路（基于 Readability / Mozilla 注泽）：
  1. DOM 结构过滤：排除 nav/footer/header/aside/script/style 等噪音标签
  2. 标签 class/id 过滤：排除含 nav|footer|sidebar|ads|comment|promo|advert|social|share 的块
  3. Text Density 过滤：计算每个块的 text_length / (link_length + 1)，
     link density > 0.5 的块视为导航/广告，丢弃
  4. Tag Importance 加权：article/main/section/p 等语义标签加权，优先保留
  5. 动态阈值筛选：低于 0.48 分值的块丢弃
  6. Boilerplate 文本清理：正则去除转载声明、编辑签名、侵权举报等残留文本

使用方式：
  from content_filter import create_content_filter, CONTENT_FILTER
  filter = create_content_filter()
  filtered_chunks = filter.filter_content(html)   # 返回 <div>...</div> 列表
"""
import re
from crawl4ai.content_filter_strategy import PruningContentFilter
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator

# 默认全局过滤器实例（单例，程序生命周期内复用）
CONTENT_FILTER: PruningContentFilter = None
MARKDOWN_GENERATOR: DefaultMarkdownGenerator = None


def create_content_filter(
    min_word_threshold: int = 5,
    threshold: float = 0.48,
    threshold_type: str = "fixed",
) -> PruningContentFilter:
    """
    创建 PruningContentFilter 实例。

    参数说明：
      min_word_threshold: 最小词数阈值，低于该值的文本块直接丢弃（默认 10）
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
    global CONTENT_FILTER
    if CONTENT_FILTER is None:
        CONTENT_FILTER = create_content_filter()
    return CONTENT_FILTER


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
    global MARKDOWN_GENERATOR
    if MARKDOWN_GENERATOR is None:
        MARKDOWN_GENERATOR = get_markdown_generator()
    return MARKDOWN_GENERATOR


# ---------------------------------------------------------------------------
# 辅助：Boilerplate 文本清理（独立于 HTML DOM 的后处理）
# ---------------------------------------------------------------------------

# 常见 Boilerplate 文本 pattern（用于 markdown 级别的二次清理）
BOILERPLATE_PATTERNS = [
    # 转载/授权声明
    (r"^(【.*?】\s*)?(转载|摘录|来源|出处|原文链接|原文地址|来源网址).*?$", re.MULTILINE | re.IGNORECASE),
    # 编辑签名
    (r"^责编：.*$", re.MULTILINE),
    (r"^责任编辑：.*$", re.MULTILINE),
    (r"^编辑：.*$", re.MULTILINE),
    (r"^作者：.*$", re.MULTILINE),
    # 举报/侵权提示
    (r"^(如需转载|转载需|转载授权|侵权举报|举报).*?$", re.MULTILINE),
    # 分隔线
    (r"^[|\-=]{3,}$", re.MULTILINE),
    # 底部二维码/关注提示
    (r"(?:扫描|长按|识别).*?(?:二维码|关注|公众|微信号).*?$", re.IGNORECASE | re.MULTILINE),
    # 版权声明
    (r"^©?\s*版权.*?$", re.MULTILINE | re.IGNORECASE),
    # 本文结束标记
    (r"^本文结束.*$", re.MULTILINE),
    # 推荐阅读/相关阅读残留
    (r"^【相关.*?】.*$", re.MULTILINE),
    # ==== 站点导航/面包屑残留 ====
    # cnenergynews.cn 等能源类网站顶部导航残留
    (r"^广告\s*人民日报主管.*?主办\s*网站地图.*?$", re.MULTILINE),
    (r"^网站地图\s*联系我们\s*首页.*?$", re.MULTILINE),
    # 数字编号导航残留 (1. 首页 2. 会议会展 3. 正文)
    (r"^\d+\.\s*(?:首页|会议会展|正文|新闻|资讯|文章)[^\n]*$", re.MULTILINE),
    # 分类导航残留 (即时新闻 能源要闻 焦点关注...)
    (r"^(?:即时新闻|能源要闻|焦点关注|能源评论|能源党建|热点专题|生态环保|人事动态|能源城市|环球视野|产业聚焦|电网电力|新能源|油气)\s*", re.MULTILINE),
    # 顶部站名/主办方残留
    (r"^人民日报主管.*?有限公司主办\s*$", re.MULTILINE),
    # 来源行残留 (来源：中国能源网2026年05月26日 17:42)
    (r"^来源[：:]\s*[^\n]+\d{4}[年-]\d{2}[月-]\d{2}[日]?\s*\d{2}:\d{2}.*$", re.MULTILINE | re.IGNORECASE),
    # 人民网底部噪音：热门排行、微信扫一扫、热门推荐
    (r"^热门排行\s*\d[^\n]+$", re.MULTILINE),
    (r"^微信[扫扫]?一扫[^\n]*$", re.MULTILINE),
    (r"^提供新闻线索[^\n]*$", re.MULTILINE),
    (r"^(?:人民智云|人民智作|热门排行|热门推荐|推荐阅读)[^>\n]*$", re.MULTILINE),
    (r"^[^\n]*-->.*$", re.MULTILINE),  # 箭头链接残留
    (r"^[^\n]*→.*$", re.MULTILINE),     # 箭头链接残留
    # 人民网底部：客户端下载、人民日报少年等
    (r"^(?:客户端下载|人民日报|人民日报少年|人民网\+|手机人民网|领导留言板|人民视频|人民智云|人民智作)[^\n]*$", re.MULTILINE),
    (r"^关注公众号[^\n]*$", re.MULTILINE),
    (r"^分享让更多人看到[^\n]*$", re.MULTILINE),
]


def _score_line(line: str) -> float:
    """
    给单行文本打分，0-1之间，分数越高越可能是正文。

    评分维度：
      1. 长度得分：短行(<10字)倾向是导航，长行更可能正文
      2. 链接密度：链接文字占比高→噪音
      3. 字符类型：汉字/中文标点占比高→正文
      4. 可读性：数字、英文、特殊符号占比高→噪音（导航/代码）
      5. 位置标记词：含"首页/新闻/资讯/关于"等→噪音
    """
    if not line or not line.strip():
        return 0.0

    line_stripped = line.strip()
    line_len = len(line_stripped)

    # 1. 长度得分：太短→低分，30-200字最佳
    if line_len < 5:
        return 0.1
    elif line_len < 15:
        length_score = 0.2
    elif line_len < 30:
        length_score = 0.5
    elif line_len < 200:
        length_score = 0.8
    else:
        length_score = 0.6

    # 2. 链接密度（[xxx](url) 或 <a>xxx</a>）
    link_pattern = r'\[[^\]]*\]\([^)]+\)|<a[^>]*>[^<]*</a>'
    link_matches = re.findall(link_pattern, line)
    link_text_len = sum(len(re.sub(r'[\[\](){}<>`]', '', m)) for m in link_matches)
    link_density = link_text_len / line_len if line_len > 0 else 0

    # 3. 字符类型得分：汉字占比高→正文
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', line_stripped))
    chinese_ratio = chinese_chars / line_len if line_len > 0 else 0

    # 4. 数字/英文占比（导航常有数字编号、URL）
    non_chinese = len(re.findall(r'[a-zA-Z0-9]', line_stripped))
    foreign_ratio = non_chinese / line_len if line_len > 0 else 0

    # 5. 噪音关键词
    noise_keywords = [
        '首页', '网站地图', '联系我们', '关于我们', '加入我们', '人才招聘',
        '广告服务', '版权所有', 'copyright', '网站备案', 'ICP证',
        '热门排行', '热门推荐', '推荐阅读', '相关阅读', '相关推荐',
        '客户端下载', '扫码下载', '微信扫一扫', '关注公众号', '分享到',
        '人民视频', '人民智云', '人民智作', '人民网+', '领导留言板',
        '人民日报少年', '手机人民网', '新闻线索', '违法和不良信息',
    ]
    noise_count = sum(1 for kw in noise_keywords if kw in line_stripped)
    noise_penalty = min(0.5, noise_count * 0.15)

    # 综合得分计算
    score = (
        length_score * 0.2
        + (1 - link_density) * 0.2
        + chinese_ratio * 0.3
        + (1 - foreign_ratio) * 0.15
        - noise_penalty
    )

    # 特定模式加分：完整句子（有标点结尾）
    if re.search(r'[。！？！？\.!?]$', line_stripped):
        score += 0.1

    return max(0.0, min(1.0, score))


def _is_noise_line(line: str) -> bool:
    """
    快速判断是否是噪音行（不需要打分）。
    """
    line_stripped = line.strip()

    # 空白行
    if not line_stripped:
        return True

    # 太短且无实质内容
    if len(line_stripped) < 3:
        return True

    # 全是分隔符/装饰符
    if re.match(r'^[|\-=•○●◆■□▪▫◦▪*]{3,}$', line_stripped):
        return True

    # 纯数字/纯英文行（太短时）
    if len(line_stripped) < 10 and re.match(r'^[a-zA-Z0-9\s\(\)\.,;:!?-]+$', line_stripped):
        return True

    return False


def clean_boilerplate_text(text: str) -> str:
    """
    对提取后的纯文本进行 boilerplate 清理。

    流程：
      1. 通用行评分过滤：低于阈值的行直接删除
      2. 正则二次清理：去除残留的 Boilerplate 文本
      3. 去重行清理：连续重复的行删除
    """
    if not text:
        return text

    lines = text.split('\n')
    cleaned_lines = []
    prev_line = ""

    for line in lines:
        line_stripped = line.strip()

        # 步骤1：快速噪音判断
        if _is_noise_line(line_stripped):
            continue

        # 步骤2：行评分过滤
        score = _score_line(line)
        if score < 0.25:  # 低于0.25分的行丢弃
            continue

        # 步骤3：去重（与上一行完全相同则跳过）
        if line_stripped == prev_line:
            continue

        cleaned_lines.append(line)
        prev_line = line_stripped

    text = '\n'.join(cleaned_lines)

    # 步骤4：正则Boilerplate清理（保留通用规则，过滤站点特定噪音）
    for pattern, flags in BOILERPLATE_PATTERNS:
        text = re.sub(pattern, "", text, flags=flags)

    # 步骤5：清理多余空行
    text = re.sub(r'\n{3,}', '\n\n', text)

    return text.strip()


def _clean_markdown_light(text: str) -> str:
    """轻度 markdown 清理：只去掉图片行和最明显的噪音，保留正文结构"""
    text = re.sub(r'!\[([^\]]*)\]\([^)]*\)', '', text)  # 删除图片行
    text = re.sub(r'\*\*([^\*]+)\*\*', r'\1', text)       # 粗体变文本
    text = re.sub(r'\*([^*]+)\*', r'\1', text)            # 斜体变文本
    text = re.sub(r'__([^_]+)__', r'\1', text)
    text = re.sub(r'_([^_]+)_', r'\1', text)
    text = re.sub(r'~~([^~]+)~~', r'\1', text)
    text = re.sub(r'`([^`]+)`', r'\1', text)
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)  # 链接变文本
    text = re.sub(r'#{1,6}\s+', '', text)                  # 去掉 markdown 标题标记
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


# ---------------------------------------------------------------------------
# 主入口函数：直接对原始 HTML 返回干净正文文本
# ---------------------------------------------------------------------------

# HTML 直接提取的备用模式（当 PruningContentFilter 无法提取时使用）
HTML_EXTRACT_PATTERNS = [
    # cnenergynews.cn 等能源类网站：<section data-type="rtext">...</section>
    (r'<section[^>]*data-type=["\']rtext["\'][^>]*>(.*?)</section>', re.DOTALL),
    # 通用：article 标签内内容
    (r'<article[^>]*>(.*?)</article>', re.DOTALL),
    # 通用：class="article-content" 或 id="article-content"
    (r'(?:class|id)=["\'][^"\']*(?:article|content|post|entry)[^"\']*["\'][^>]*>(.*?)</(?:div|p|article)>', re.DOTALL),
    # 通用：<div class="content">...</div>
    (r'<div[^>]+class=["\'][^"\']*content[^"\']*["\'][^>]*>([\s\S]{200,})</div>', re.DOTALL),
]


def _extract_by_html_pattern(html: str) -> str:
    """
    当 PruningContentFilter 失效时，直接用正则从 HTML 提取正文。
    """
    import html as html_module

    for pattern, flags in HTML_EXTRACT_PATTERNS:
        m = re.search(pattern, html, flags)
        if m:
            block = m.group(1)
            # 去除标签，保留文字
            text = re.sub(r'<[^>]+>', '', block)
            text = html_module.unescape(text)
            text = re.sub(r'\s+', ' ', text).strip()
            if len(text) >= 100:
                return text
    return ""


def extract_clean_content(html: str, base_url: str = "") -> str:
    """
    完整流程：对任意数据源的 HTML → 返回干净正文文本。

    流程：
      1. PruningContentFilter 过滤 HTML DOM 结构
      2. DefaultMarkdownGenerator 生成 fit_markdown
      3. fit_markdown 不足50字 → raw_markdown 轻度清理
      4. 仍不足 → 直接正则从 HTML 提取正文
      5. clean_boilerplate_text 二次清理残留 boilerplate

    参数：
      html: 原始 HTML 字符串
      base_url: 用于链接修复的基准 URL（可选）

    返回：
      干净的文章正文（纯文本 markdown）
    """
    if not html or not html.strip():
        return ""

    content_filter = get_content_filter()
    md_generator = get_markdown_generator(content_filter=content_filter)

    result = md_generator.generate_markdown(
        input_html=html,
        base_url=base_url,
        citations=False,  # 采集场景不需要引用标记
    )

    fit_md = result.fit_markdown or ""
    if not fit_md or len(fit_md.strip()) < 50:
        # Fallback 1: raw_markdown 轻度清理
        raw_md = result.raw_markdown or ""
        if raw_md and len(raw_md) > 100:
            text = _clean_markdown_light(raw_md)
            text = clean_boilerplate_text(text)
            if len(text) >= 50:
                return text.strip()
        # Fallback 2: 直接从 HTML 提取正文
        text = _extract_by_html_pattern(html)
        if text:
            text = clean_boilerplate_text(text)
            return text.strip()
        # 确实无法提取，返回空
        return ""

    # 检查 fit_md 是否为 boilerplate 残渣（footer/版权/投稿信息）
    boilerplate_indicators = [
        '投稿', '责任编辑', '版权', '版权所有', '中国能源网',
        '联系电话', '邮箱:', '微信/', 'qq.com',
    ]
    boilerplate_ratio = sum(1 for kw in boilerplate_indicators if kw in fit_md) / len(boilerplate_indicators)
    if boilerplate_ratio >= 0.3 or len(fit_md.strip()) < 100:
        # 视为无效提取，尝试 HTML 正则提取
        raw_md = result.raw_markdown or ""
        if raw_md and len(raw_md) > 100:
            text = _clean_markdown_light(raw_md)
            text = clean_boilerplate_text(text)
            if len(text) >= 100:
                return text.strip()
        text = _extract_by_html_pattern(html)
        if text:
            text = clean_boilerplate_text(text)
            return text.strip()
        return ""

    # 转换为纯文本
    text = fit_md
    text = re.sub(r"\*+([^*]+)\*+", r"\1", text)
    text = re.sub(r"__([^_]+)__", r"\1", text)
    text = re.sub(r"_([^_]+)_", r"\1", text)
    text = re.sub(r"~~([^~]+)~~", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"!\[([^\]]*)\]\([^)]*\)", "", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = clean_boilerplate_text(text)

    return text.strip()


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python content_filter.py <html_file>")
        sys.exit(1)

    html_path = sys.argv[1]
    html_content = open(html_path, encoding="utf-8").read()
    clean = extract_clean_content(html_content)
    print(clean[:500])
    print(f"\n--- Total: {len(clean)} chars ---")
