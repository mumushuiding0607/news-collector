"""
js_render_fixes.py - JS 渲染站点采集增强模块

本模块隔离了所有与 JS 渲染站点相关的配置，
在 news-collector 旧架构中通过 build_js_run_cfg() 为特定站点返回增强配置。

包含：
1. JS_RENDER_SOURCES - 需要增强配置的站点及其参数
2. build_js_run_cfg() - 为指定数据源构建增强配置（返回 None 表示用默认配置）
"""

from crawl4ai import CrawlerRunConfig
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
import sys
from pathlib import Path

# 添加项目根目录到 path（确保 content_filter 可导入）
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from common.content_filter import get_content_filter

# ---------------------------------------------------------------------------
# JS 渲染增强配置
# ---------------------------------------------------------------------------

JS_RENDER_SOURCES: dict[str, dict] = {
    "人民网": {
        "wait_until": "networkidle",
        "delay": 8.0,
    },
    "美联储官网": {
        "wait_until": "networkidle",
        "delay": 8.0,
    },
    "中国电子元件": {
        "wait_until": "networkidle",
        "delay": 8.0,
    },
    "农业农村部": {
        "wait_until": "networkidle",
        "delay": 8.0,
    },
}


def build_js_run_cfg(source_name: str) -> CrawlerRunConfig | None:
    """
    为 JS 渲染站点构建增强版 CrawlerRunConfig。

    Args:
        source_name: 数据源名称

    Returns:
        增强配置（CrawlerRunConfig），非 JS 站点返回 None（使用调用方默认配置）
    """
    js_cfg = JS_RENDER_SOURCES.get(source_name)
    if not js_cfg:
        return None

    return CrawlerRunConfig(
        word_count_threshold=50,
        verbose=False,
        delay_before_return_html=js_cfg["delay"],
        wait_until=js_cfg.get("wait_until", "networkidle"),
        markdown_generator=DefaultMarkdownGenerator(
            content_filter=get_content_filter()
        ),
    )


if __name__ == "__main__":
    print("JS 渲染增强配置：")
    for name, cfg in JS_RENDER_SOURCES.items():
        print(f"  - {name}: wait_until={cfg['wait_until']}, delay={cfg['delay']}s")
