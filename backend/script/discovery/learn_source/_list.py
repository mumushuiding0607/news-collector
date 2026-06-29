# _list.py - 列表发现相关 phase
import asyncio
from urllib.parse import urlencode, urlparse

from script.discovery.list_discovery import discover_list_config, log
from script.discovery.util.html_fetch import fetch_list_html as _fetch_list_html_async

# 已确认失效的列表配置类型：保留只会浪费尝试，必须重新学习
OBSOLETE_LIST_TYPES = ("ajax", "api", "column", "cctv")


def fetch_list_html(url: str) -> str:
    """Step 1.1: 抓取列表页（统一走 fetch_list_html 入口，自动等待 JS 渲染）"""
    log(f"[Step 1.1] 抓取列表页: {url}")
    _, list_html = asyncio.run(_fetch_list_html_async(url))
    if not list_html:
        log(f"[Step 1.1] 列表页抓取失败: {url}")
        return ""
    log(f"[Step 1.1] 列表页抓取成功，HTML长度={len(list_html)}")
    return list_html


def discover_list_with_policy(
    url: str,
    list_html: str,
    existing_list_config: dict | None,
    headline: str,
    force_relearn: bool,
) -> tuple[dict | None, str | None, str | None]:
    """Step 1.2/2: 列表发现，根据已有配置和 force_relearn 决定保留/覆盖

    流程：API 发现 → HTML LLM 发现（含 raw_fetch 兜底）

    force_relearn 语义：
      - True：完全重新学习，任何阶段都不回退到现有配置（包括 API/HTML LLM 失败时）
      - False：尽量保留现有配置（除非类型已废弃）
    """
    # Step 1.5: API 发现（通用 find_api + 验证 + 字段映射）
    # 始终无条件运行：哪怕有现有 api 配置，也要重跑以捕获端点/字段变化
    api_result = discover_api_with_policy(url, list_html, headline)
    if api_result[0] is not None:
        return api_result

    # force_relearn=True 时，不回退到现有配置
    if force_relearn:
        log("[Step 1.2/2] force_relearn=True，不回退到现有配置")
        list_config, source_type, method = _run_list_discovery(url, list_html, headline, force_relearn=True)
        if list_config is None:
            log("[统一学习] HTML LLM 学习失败，force_relearn=True，不保留已有配置")
            # 返回 None，让 save_learned_config 失败
            return None, None, "学习失败"
        return list_config, source_type, method

    # force_relearn=False 时的保留策略
    if existing_list_config:
        existing_type = existing_list_config.get("type") if isinstance(existing_list_config, dict) else None
        if existing_type in OBSOLETE_LIST_TYPES:
            log(f"[Step 1.2/2] 已有配置 type={existing_type}，不再保留，强制重新学习")
            return _run_list_discovery(url, list_html, headline, force_relearn=True)

        log(f"[Step 1.2/2] 已有配置 type={existing_type}，尝试学习是否有更好配置...")
        list_config, source_type, method = _run_list_discovery(url, list_html, headline)
        if list_config is None:
            list_config = existing_list_config
            method = "已有配置"
            log(f"[统一学习] 学习失败，保留已有配置: type={list_config.get('type')}")
        return list_config, source_type, method

    log("[Step 1.2/2] 开始列表发现...")
    list_config, source_type, method = _run_list_discovery(url, list_html, headline)
    if list_config is None:
        log("[统一学习] 列表发现失败，将仅提取样本新闻用于验证")
    return list_config, source_type, method


def _run_list_discovery(url: str, list_html: str, headline: str, force_relearn: bool = False) -> tuple[dict | None, str | None, str | None]:
    """调用 discover_list_config 并解析 discovery_method"""
    discovered = discover_list_config(url, list_html, use_raw_fallback=True, headline=headline, force_relearn=force_relearn)
    if not discovered:
        return None, None, "学习失败"

    saved_source_type = discovered.get("source_type") if isinstance(discovered, dict) else None
    lc = discovered.get("list_config") if isinstance(discovered, dict) and "list_config" in discovered else discovered

    if isinstance(lc, dict):
        if lc.get("type") == "raw":
            method = "raw_fetch"
        elif lc.get("type") == "column":
            method = "API"
        else:
            method = "LLM分析"
    else:
        method = "LLM分析"

    log(f"[统一学习] 列表发现成功 [{method}]: {discovered.get('name')} ({discovered.get('source_type')})")
    return discovered, saved_source_type, method


# ==================== API 发现（通用 JSONP/REST 端点）====================

def discover_api_with_policy(
    url: str,
    list_html: str,
    headline: str,
) -> tuple[dict | None, str | None, str | None]:
    """
    Step 1.5: API 发现。

    1. find_api：正则扫 HTML 找 API 候选 + 4 条规则验证（数组/URL/时间/中文>10）
    2. analyze_api_params：找日期参数 + 验证（today/yesterday 都有数据）
    3. fetch_api_sample：date=today 取样本 + 客户端过滤当天
    4. discover_api_field_mapping：值识别 → LLM 补缺

    任意一步失败即回退到 HTML LLM 流。

    Returns:
        (list_config, source_type, method) 三元组，API 流失败时 list_config=None
    """
    from script.discovery.util.find_api import find_api
    from script.discovery.util.analyze_api import analyze_api_params, AnalyzeError
    from script.discovery.util.map_api_fields import fetch_api_sample, discover_api_field_mapping

    try:
        candidates = find_api(list_html, base_url=url, headline=headline)
    except Exception as e:
        log(f"[Step 1.5] find_api 异常: {e}，回退到 HTML 流")
        return None, None, None

    if not candidates:
        log("[Step 1.5] 未找到 API 候选，回退到 HTML 流")
        return None, None, None

    cand = candidates[0]
    base_url = cand["url"]
    full_url = base_url + "?" + urlencode(cand["params"], doseq=True) if cand.get("params") else base_url
    name = cand.get("title") or url  # title 在 find_api 里没填，用 url 占位
    log(f"[Step 1.5] 命中 API: {full_url[:120]}")

    # 2. 分析日期参数
    try:
        analysis = analyze_api_params(full_url)
    except AnalyzeError as e:
        log(f"[Step 1.5] 日期参数分析失败: {e}，回退到 HTML 流")
        return None, None, None
    except Exception as e:
        log(f"[Step 1.5] analyze_api 异常: {e}，回退到 HTML 流")
        return None, None, None

    log(f"[Step 1.5] 日期参数: {analysis['date_param']} ({analysis['date_format']}), "
        f"today={analysis.get('today_items')}, yesterday={analysis.get('yesterday_items')}")

    # 3. 取样本（date=today，客户端过滤）
    try:
        sample = fetch_api_sample(base_url, analysis)
    except Exception as e:
        log(f"[Step 1.5] fetch_api_sample 失败: {e}，回退到 HTML 流")
        return None, None, None

    if not sample["items"]:
        log(f"[Step 1.5] 样本无当天数据 (raw={sample['raw_count']})，回退到 HTML 流")
        return None, None, None

    log(f"[Step 1.5] 样本: raw={sample['raw_count']}, today={sample['today_count']}")

    # 4. 字段映射
    try:
        result = discover_api_field_mapping(
            sample["items"],
            api_url=full_url,
            name=name,
            analysis=analysis,
        )
    except Exception as e:
        log(f"[Step 1.5] 字段映射失败: {e}，回退到 HTML 流")
        return None, None, None

    log(f"[Step 1.5] field_mapping: {result['field_mapping']}")

    # 5. 转换为统一的 list_config 包装格式
    #    与 _run_list_discovery 输出一致：{source_type, list_config: {type, ...}, article, name, publish_time_pattern}
    list_config_inner = _build_api_list_config(result, analysis, full_url)
    wrapped = {
        "name": result.get("name", name),
        "source_type": "api",
        "publish_time_pattern": "",
        "article": result.get("article", {}),
        "list_config": list_config_inner,
    }

    log(f"[统一学习] 列表发现成功 [API发现]: {wrapped['name']} (api)")
    return wrapped, "api", "API发现"


def _build_api_list_config(result: dict, analysis: dict, full_url: str) -> dict:
    """
    把新 API 发现结果转换为 crawl_api_source 期望的 list_config 格式。

    result 来自 discover_api_field_mapping：
        {field_mapping: {url, title, publish_time, summary}, api: {...}, ...}

    输出：
        {
            "type": "api",
            "endpoint": "...",
            "params": {...},
            "field_mapping": {url, title, date, summary},  # 注意 date 不是 publish_time
            "pagination": {"max_pages": 10},
        }
    """
    fm = result.get("field_mapping", {})
    api_section = result.get("api", {})

    date_param = api_section.get("date_param", analysis.get("date_param", ""))
    date_format = api_section.get("date_format", analysis.get("date_format", ""))
    params = api_section.get("params", analysis.get("params", {}))

    return {
        "type": "api",
        # endpoint 必须是 base URL（不含 query），否则 fetch_api_page 会重复拼参数
        "endpoint": _strip_query(api_section.get("url", full_url)),
        "method": api_section.get("method", "GET"),
        # params 里的日期值清空（占位符），由爬虫在调用时按 date_format 注入
        # 避免存"20260618"这种学习当天的固定值（看起来像写死，且明天跑会拿旧数据）
        "params": _clear_date_value(params, date_param),
        "date_param": date_param,
        "date_format": date_format,
        "field_mapping": {
            "url": fm.get("url", "url"),
            "title": fm.get("title", "title"),
            "date": fm.get("publish_time", "time"),  # 兼容旧 crawl_api_source
            "summary": fm.get("summary", "brief"),
        },
        "pagination": {"max_pages": 10},
    }


def _clear_date_value(params: dict, date_param: str) -> dict:
    """把 params[date_param] 置空，避免存储学习当天的固定日期值。

    爬虫在调用时按 date_format 格式化 target_date 后填回。
    """
    p = dict(params)
    if date_param and date_param in p:
        p[date_param] = ""
    return p


def _strip_query(url: str) -> str:
    """去掉 URL 的 query string，只保留 scheme://host/path。"""
    p = urlparse(url)
    return f"{p.scheme}://{p.netloc}{p.path}"


def apply_list_complete(list_config: dict | None, skip_article_crawler: bool) -> dict | None:
    """Step 2.1: skip_article_crawler=True 时把 list_complete=True 写入 list_config"""
    if not skip_article_crawler or not list_config:
        return list_config
    lc = list_config.get("list_config") if isinstance(list_config, dict) and "list_config" in list_config else list_config
    if lc and isinstance(lc, dict):
        lc["list_complete"] = True
        log("[统一学习] 已设置 list_complete=True，跳过正文学习")
    return list_config
