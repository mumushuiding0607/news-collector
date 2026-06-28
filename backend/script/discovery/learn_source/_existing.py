# _existing.py - 加载已有配置
import json

from script.db.sources_db import get_crawl_config_by_url
from script.discovery.list_discovery import log


def load_existing_config(url: str) -> tuple[dict | None, dict | None]:
    """加载已有 list_config 和 content_extract（若有）"""
    existing_list_config = None
    existing_content_extract = None
    try:
        # list_config / content_extract 在 source_crawl_configs 表，不在 sources 表
        # 旧实现用 get_source_by_url（查 sources 表，没有 list_config 列），导致一直返回 None
        existing = get_crawl_config_by_url(url)
        if existing:
            lc = existing.get("list_config")
            if lc:
                existing_list_config = json.loads(lc) if isinstance(lc, str) else lc
            ce = existing.get("content_extract")
            if ce:
                existing_content_extract = json.loads(ce) if isinstance(ce, str) else ce
            log(
                f"[统一学习] 已有配置: list_config="
                f"{existing_list_config.get('type') if existing_list_config else 'None'}, "
                f"content_extract={'有' if existing_content_extract else '无'}, "
                f"source_type={existing.get('source_type', 'None')}"
            )
    except Exception as e:
        log(f"[统一学习] 加载已有配置异常: {e}")
    return existing_list_config, existing_content_extract