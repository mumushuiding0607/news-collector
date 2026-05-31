"""
prompts.py - Prompt 模板管理

集中管理所有 LLM prompt 模板，支持从文件加载。
"""

import logging
from pathlib import Path
from typing import Callable

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 模板路径
# ---------------------------------------------------------------------------

_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompt"


def _load_template(filename: str) -> str:
    """从 prompt 目录加载模板文件"""
    path = _PROMPTS_DIR / filename
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        logger.error("Prompt 模板未找到: %s", path)
        raise


# ---------------------------------------------------------------------------
# Prompt 模板
# ---------------------------------------------------------------------------

def get_rag_prompt(sector: str) -> str:
    """
    获取生成板块核心标的报告的 prompt。

    Args:
        sector: 板块名称

    Returns:
        填充后的 prompt 字符串
    """
    template = _load_template("核心标的.md")
    return template.replace("【目标板块】", f"【{sector}】")


def get_news_filter_prompt(news_content: str) -> str:
    """
    获取新闻过滤的 prompt。

    Args:
        news_content: 新闻正文内容

    Returns:
        填充后的 prompt 字符串
    """
    template = _load_template("新闻过滤.md")
    return template.replace("【新闻内容】", news_content)


