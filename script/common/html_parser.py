"""
html_parser.py - 基于 sources.json 的 contentExtract 正则提取正文

功能：
  读取 sources.json 中各数据源的 contentExtract 字段（正则表达式），
  提供统一的 HTML 正文提取接口。

前置依赖：
  - config/sources.json 中需有数据源的 contentExtract 字段
  - 无需额外安装，标准库即可运行

使用示例：
  # 方式1：直接提取
  from common.html_parser import extract_by_source
  content = extract_by_source(html, "中国能源网", base_url="https://example.com")
  if content:
      print(f"提取到 {len(content)} 字正文")
  else:
      print("提取失败，该数据源未配置正则或正则无法匹配")

  # 方式2：预加载正则表
  from common.html_parser import load_content_extract_patterns
  patterns = load_content_extract_patterns()
  for name, pat in patterns.items():
      print(f"  {name}: {pat[:60]}...")

  # 方式3：尝试多个数据源
  from common.html_parser import extract_by_sources
  results = extract_by_sources(html, ["中国能源网", "快科技", "人民网"])
  for name, text in results.items():
      print(f"  {name} 提取成功：{len(text)} 字")

配置来源：
  sources.json 中每个数据源的 contentExtract 字段，示例：
  {
    "name": "中国能源网",
    "url": "https://cnenergynews.cn/",
    "contentExtract": "<article[^>]*>(.*?)</article>"
  }

contentExtract 正则由 html_pattern_learner.py 自动生成。
"""

import json
import re
import html as html_module
from pathlib import Path
from typing import Optional

# sources.json 路径（相对于项目根目录）
SOURCES_PATH = Path(__file__).parent.parent.parent / "config" / "sources.json"

# 全局缓存：source_name -> regex pattern string
_CONTENT_PATTERNS: dict[str, str] = {}
_PATTERNS_LOADED = False


# ==================== 加载配置 ====================

def load_content_extract_patterns() -> dict[str, str]:
    """
    加载所有数据源的 contentExtract 正则表达式。

    使用全局缓存，同一进程内只读取一次文件。

    Returns:
        {source_name: pattern} 字典，无配置时返回空字典
    """
    global _CONTENT_PATTERNS, _PATTERNS_LOADED
    if _PATTERNS_LOADED:
        return _CONTENT_PATTERNS

    if not SOURCES_PATH.exists():
        return {}

    try:
        data = json.loads(SOURCES_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}

    for source in data.get("sources", []):
        name = source.get("name", "")
        pattern = source.get("contentExtract", "")
        if name and pattern:
            _CONTENT_PATTERNS[name] = pattern

    _PATTERNS_LOADED = True
    return _CONTENT_PATTERNS


# ==================== 提取正文 ====================

def extract_by_source(
    html: str,
    source_name: str,
    base_url: str = "",
    patterns: dict[str, str] = None,
) -> str:
    """
    使用指定数据源的 contentExtract 正则从 HTML 中提取正文。

    提取流程：
      1. 查找该数据源对应的正则
      2. 用正则 search HTML（re.DOTALL 模式）
      3. 去除 HTML 标签，保留纯文本
      4. HTML 实体解码（&amp; &lt; 等）
      5. 清理多余空白

    Args:
        html: 原始 HTML 字符串
        source_name: 数据源名称（与 sources.json 中的 name 匹配）
        base_url: 基准 URL（当前未使用，保留接口兼容性）
        patterns: 可选，预加载的 pattern 字典（避免重复加载文件）

    Returns:
        提取的正文文本（已去除HTML标签），失败返回空字符串
    """
    if not html or not html.strip():
        return ""

    if patterns is None:
        patterns = load_content_extract_patterns()

    pattern = patterns.get(source_name, "")
    if not pattern:
        return ""

    try:
        compiled = re.compile(pattern, re.DOTALL)
    except re.error:
        return ""

    m = compiled.search(html)
    if not m:
        return ""

    # 优先使用捕获组，如果没有捕获组则使用整个匹配
    # 如果有多个捕获组，选择第一个非空的
    block = None
    if m.lastindex and m.lastindex >= 1:
        for i in range(1, m.lastindex + 1):
            g = m.group(i)
            if g:
                block = g
                break
    if block is None:
        block = m.group(0)

    if not block:
        return ""

    # 先去除 <style>...</style> 块（内含 CSS 不应混入正文）
    block = re.sub(r'<style[^>]*>[\s\S]*?</style>', '', block)
    # 去除HTML标签，保留文字
    text = re.sub(r'<[^>]+>', '', block)
    # HTML实体解码
    text = html_module.unescape(text)
    # 清理多余空白
    text = re.sub(r'\s+', ' ', text).strip()

    return text


def extract_by_sources(
    html: str,
    source_names: list[str],
    base_url: str = "",
) -> dict[str, str]:
    """
    尝试用多个数据源的正则提取正文，成功即返回。

    按列表顺序依次尝试，一旦成功立即返回结果。
    用于不确定数据源名称时的兜底提取。

    Args:
        html: 原始 HTML 字符串
        source_names: 数据源名称列表（按优先级排序）
        base_url: 基准 URL

    Returns:
        {source_name: extracted_text}，只包含成功提取的
    """
    patterns = load_content_extract_patterns()
    results = {}

    for name in source_names:
        if name not in patterns:
            continue
        text = extract_by_source(html, name, base_url, patterns)
        if text and len(text) >= 50:
            results[name] = text

    return results


# ==================== 查询接口 ====================

def get_pattern(source_name: str) -> Optional[str]:
    """
    获取指定数据源的正则表达式。

    Args:
        source_name: 数据源名称

    Returns:
        正则字符串，未配置返回 None
    """
    patterns = load_content_extract_patterns()
    return patterns.get(source_name)


# ==================== CLI 测试 ====================

if __name__ == "__main__":
    import sys

    patterns = load_content_extract_patterns()
    if not patterns:
        print("未找到任何 contentExtract 正则表达式")
        print("请先运行 html_pattern_learner.py 为数据源生成正则")
        sys.exit(0)

    print(f"已加载 {len(patterns)} 个数据源的正则表达式：")
    for name, pat in patterns.items():
        print(f"  - {name}: {pat[:60]}...")