# _save.py - 保存到数据库 + 构造返回结果
import json

from script.db.sources_db import upsert_crawl_config
from script.discovery.list_discovery import log


def save_learned_config(
    url: str,
    name: str,
    list_config: dict | None,
    content_config: dict,
) -> bool:
    """Step 5: 保存到 source_crawl_configs 表"""
    import sys as _sys
    print(f"[DEBUG save_learned_config] list_config id={id(list_config) if list_config else None}, url_pattern={list_config.get('url_pattern') if list_config else None}", file=_sys.stderr)
    if list_config is None:
        log("[统一学习] 无配置且无样本新闻，放弃保存")
        return False

    try:
        saved_list_config, saved_source_type = extract_saved_list_config(list_config)
        print(f"[DEBUG save_learned_config] saved_list_config id={id(saved_list_config) if saved_list_config else None}, url_pattern={saved_list_config.get('url_pattern') if saved_list_config else None}", file=_sys.stderr)

        ce = content_config.get("content_extract") if content_config else None
        pt = _resolve_publish_time_pattern(content_config, saved_list_config)

        upsert_crawl_config(
            url=url,
            name=name,
            source_type=saved_source_type,
            list_config=saved_list_config,
            content_extract=json.dumps(ce) if ce else None,
            publish_time_pattern=pt,
        )
        log("[统一学习] 已保存到 source_crawl_configs")
        return True
    except Exception as e:
        log(f"[统一学习] 保存失败: {e}")
        return False


def extract_saved_list_config(list_config: dict | None) -> tuple[dict | None, str | None]:
    """从 list_config 中提取要入库的 list_config 子字典和 source_type"""
    if not list_config:
        return None, None
    if isinstance(list_config, dict) and "list_config" in list_config:
        nested = list_config.get("list_config")
        # 如果 url_pattern/type 在外层但不在内层，需要拷贝过去
        # (_set_url_pattern 在外层设置了 url_pattern 和 type='api')
        if isinstance(nested, dict):
            if list_config.get("url_pattern") and not nested.get("url_pattern"):
                nested["url_pattern"] = list_config["url_pattern"]
            if list_config.get("type") == "api" and nested.get("type") != "api":
                nested["type"] = "api"
            # 外层 article 有有效 URL（网络捕获 discovered）时，覆盖嵌套的 article
            outer_article = list_config.get("article") or {}
            if outer_article and outer_article.get("url") and outer_article.get("url") != outer_article.get("title", ""):
                nested["article"] = outer_article
        return nested, list_config.get("source_type")
    return list_config, None


def _resolve_publish_time_pattern(content_config: dict | None, saved_list_config: dict | None) -> str | None:
    """优先正文学习的 pattern，否则用列表的 pattern"""
    pt = content_config.get("publish_time_pattern") if content_config else None
    if not pt and saved_list_config and isinstance(saved_list_config, dict):
        pt = saved_list_config.get("publish_time_pattern")
    return pt


def build_result(
    name: str,
    url: str,
    list_config: dict | None,
    content_config: dict,
    saved_source_type: str | None,
    discovery_method: str | None,
    article_url: str | None,
    article_title: str | None,
    sample_news: list,
    skip_article_crawler: bool,
) -> dict:
    """组装返回结果字典"""
    ce = content_config.get("content_extract") if content_config else None
    saved_list_config, _ = extract_saved_list_config(list_config)
    pt = _resolve_publish_time_pattern(content_config, saved_list_config)

    return {
        "name": name,
        "url": url,
        "source_type": saved_source_type,
        "discovery_method": discovery_method,
        "list_config": saved_list_config,
        "content_extract": ce,
        "publish_time_pattern": pt,
        "article_url": article_url,
        "article_title": article_title,
        "list_complete": skip_article_crawler,
        "sample_news": sample_news,
    }