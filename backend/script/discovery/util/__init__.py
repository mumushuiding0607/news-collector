"""
discovery/util - 新闻列表提取工具

从渲染后的HTML中，根据标题/关键字逆推新闻列表位置并提取内容。
"""
from .list_extractor import extract_news_list_from_rendered_html, extract_from_file, extract_as_dict
from .json_extractor import find_embedded_json, extract_json_array, extract_json_object
from .learning_log import get_learning_log_dir, save_learning_html
from .html_fetch import fetch_rendered_html, extract_html_links, extract_html_links_with_titles
from .validation import is_valid_news_url, is_valid_news_sample
from .sample_log import log_sample_news
from .css_selector import build_css_selector

__all__ = [
    # 列表提取
    "extract_news_list_from_rendered_html",
    "extract_from_file",
    "extract_as_dict",
    # JSON 提取
    "find_embedded_json",
    "extract_json_array",
    "extract_json_object",
    # 学习日志
    "get_learning_log_dir",
    "save_learning_html",
    # HTML 抓取
    "fetch_rendered_html",
    "extract_html_links",
    "extract_html_links_with_titles",
    # 验证
    "is_valid_news_url",
    "is_valid_news_sample",
    # 日志
    "log_sample_news",
    # CSS 选择器
    "build_css_selector",
]