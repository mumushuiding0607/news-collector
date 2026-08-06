"""
crawl_config.py - 爬虫配置统一读取

所有爬虫配置必须通过此模块读取，禁止在其他爬虫模块中直接读文件。
"""
from __future__ import annotations
import json
from pathlib import Path

from script.bootstrap import is_ai_news_db

# 正确路径：config/ 在 backend/ 下，与 bootstrap 的 APP_ROOT / "config" 不同
_SOURCES_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "sources.json"
_sources_data: dict | None = None
_cached_config: dict | None = None


def _load() -> dict:
    global _sources_data
    if _sources_data is None:
        _sources_data = json.loads(_SOURCES_PATH.read_text(encoding="utf-8"))
    return _sources_data


def get_crawl_config() -> dict:
    """返回爬虫相关配置，根据当前新闻类型返回对应配置"""
    global _cached_config
    if _cached_config is None:
        data = _load()
        news_type = "AI新闻" if is_ai_news_db() else "股市新闻"
        type_config = data.get(news_type, {})

        _cached_config = {
            "crawNumPerSource": type_config.get("crawNumPerSource", 30),
            "maxConsecutiveNonToday": type_config.get("maxConsecutiveNonToday", 10),
            "maxArticlesPerSource": type_config.get("maxArticlesPerSource", 500),
            "maxSourceConcurrency": type_config.get("maxSourceConcurrency", 5),
            "htmlFallbackArticles": type_config.get("htmlFallbackArticles", 50),
            "titleMinLength": type_config.get("titleMinLength", 10),
            "days": type_config.get("days", 0),
            # LLM 相关配置保持全局
            "llmBatchSize": data.get("llmBatchSize", 20),
            "llmTimeout": data.get("llmTimeout", 120),
            "llmMaxRetries": data.get("llmMaxRetries", 3),
            "newsFilterTimeout": data.get("newsFilterTimeout", 120),
            "scorerTimeout": data.get("scorerTimeout", 120),
            "findStocksTimeout": data.get("findStocksTimeout", 120),
        }
    return _cached_config


def get_list_page_extract_cfg() -> dict | None:
    """返回列表页直采配置"""
    return _load().get("listPageExtract")


def get_source_content_extract(source_name: str) -> str | None:
    """从 sources.json 获取指定数据源的 contentExtract 正则"""
    for s in _load().get("sources", []):
        if s.get("name") == source_name:
            ce = s.get("contentExtract", "")
            return ce if ce else None
    return None


def get_source_is_flash(source_name: str) -> bool:
    """从 sources.json 获取指定数据源的 is_flash 标志"""
    for s in _load().get("sources", []):
        if s.get("name") == source_name:
            return bool(s.get("is_flash", False))
    return False
