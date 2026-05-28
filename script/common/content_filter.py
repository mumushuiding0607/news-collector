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
    min_word_threshold: int = 10,
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
]


def clean_boilerplate_text(text: str) -> str:
    """
    对提取后的纯文本进行 boilerplate 清理。
    使用正则逐条匹配并删除匹配行。
    """
    for pattern, flags in BOILERPLATE_PATTERNS:
        text = re.sub(pattern, "", text, flags=flags)
    text = re.sub(r"\n{3,}", "\n\n", text)
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
def extract_clean_content(html: str, base_url: str = "") -> str:
    """
    完整流程：对任意数据源的 HTML → 返回干净正文文本。

    流程：
      1. PruningContentFilter 过滤 HTML DOM 结构
      2. DefaultMarkdownGenerator 生成 fit_markdown
      3. clean_boilerplate_text 二次清理残留 boilerplate

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
        # Fallback: fit_markdown 为空或极短 → 尝试 raw_markdown（轻度清理）
        raw_md = result.raw_markdown or ""
        if raw_md and len(raw_md) > 100:
            text = _clean_markdown_light(raw_md)
            text = clean_boilerplate_text(text)
            if len(text) >= 50:
                return text.strip()
        # 确实无法提取，返回空
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
