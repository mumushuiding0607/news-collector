"""
API Routes - News endpoints

使用 backend/core/NewsService 提供新闻数据接口。
缓存和业务逻辑已在服务层处理，数据源过滤在返回前端前统一处理。
"""
from pathlib import Path
import re

from fastapi import APIRouter, Request, HTTPException, Query

from backend.core.news_service import NewsService
from script.common.jsonutil import parse_json_field
from script.db.primary_source import mark_useful as _mark_useful

router = APIRouter()

_CACHE_DIR = Path(__file__).resolve().parent.parent / "cache"
_CACHE_DIR.mkdir(exist_ok=True)
LATEST_CACHE = _CACHE_DIR / "news_latest.json"
HISTORY_CACHE = _CACHE_DIR / "news_history.json"
HOT_CACHE = _CACHE_DIR / "news_hot.json"
SUMMARY_CACHE = _CACHE_DIR / "news_summary.json"


def _load_news_cache_config() -> dict:
    """从 sources.json 加载新闻缓存配置"""
    import json
    cfg_path = Path(__file__).resolve().parent.parent / "config" / "sources.json"
    if not cfg_path.exists():
        return {}
    try:
        data = json.loads(cfg_path.read_text(encoding="utf-8"))
        return data.get("newsCache", {})
    except Exception:
        return {}


def _get_user_id(request: Request) -> int | None:
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not token:
        return None
    from core.auth_service import get_user_by_token
    user = get_user_by_token(token)
    return user[0] if user else None


def _load_cached_json(path: Path) -> dict | None:
    if path.exists():
        try:
            import json
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


def _load_summary_from_cache() -> dict | None:
    """从缓存加载简报，加载失败返回 None"""
    if not SUMMARY_CACHE.exists():
        return None
    try:
        import json
        data = json.loads(SUMMARY_CACHE.read_text(encoding="utf-8"))
        if data and isinstance(data, dict) and data.get("date"):
            return data
        return None
    except Exception:
        return None


def _save_summary_to_cache(data: dict) -> None:
    """保存简报到缓存"""
    try:
        import json
        SUMMARY_CACHE.parent.mkdir(parents=True, exist_ok=True)
        SUMMARY_CACHE.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


@router.get("/news/summary")
def get_news_summary(
    request: Request,
    date: str | None = Query(None),
    type: str | None = Query(None),
):
    """
    获取简报内容：
    - 传 date+type：精确读取指定条目（走 DB，不走缓存）
    - 不传参：返回最新一条（优先用缓存，缓存缺失则查 DB 并回填）
    """
    if date and type:
        from script.db.anomaly_summary_db import get_summary_by_date_and_type
        db_data = get_summary_by_date_and_type(date, type)
        if db_data is None:
            return {"data": None, "message": "暂无简报"}
        return {"data": _flatten_summary(db_data)}

    data = _load_summary_from_cache()
    if data is not None and data.get("main_stimulus") is not None:
        return {"data": data}

    from script.db.anomaly_summary_db import get_latest_summary
    db_data = get_latest_summary()
    if db_data is None:
        return {"data": None, "message": "暂无简报"}

    cache_data = _flatten_summary(db_data)
    _save_summary_to_cache(cache_data)
    return {"data": cache_data}


def _flatten_summary(db_data: dict) -> dict:
    """将 summary 表行扁平化为 API 响应字段"""
    content = db_data.get("content") or {}
    return {
        "date": db_data.get("date", ""),
        "type": db_data.get("type", "异动简报"),
        "summary": content.get("summary", ""),
        "main_stimulus": content.get("main_stimulus", ""),
        "correlation": content.get("correlation", ""),
        "insights": content.get("insights", ""),
        "total_news": content.get("total_news"),
    }


@router.get("/news/summary/list")
def get_news_summary_list(request: Request, page: int = 1, limit: int = 20):
    """
    获取简报列表：
    1. 优先从 news_summary.json 缓存读取（最新简报）
    2. 缓存为空则从数据库查询（按日期分组，每日期只保留最新一条）
    """
    import json

    # 尝试从缓存读取
    cache_item = None
    cache_data = _load_summary_from_cache()
    if cache_data is not None:
        cache_item = {
            "date": cache_data.get("date", ""),
            "type": cache_data.get("type", "异动简报"),
            "created_at": "",
        }

    # 从数据库读取列表（按日期去重，每日期最新一条）
    from script.db.anomaly_summary_db import list_summaries_by_date
    db_result = list_summaries_by_date(page=page, limit=limit)

    # 如果缓存有内容且数据库为空，优先返回缓存
    if cache_item and db_result.get("total", 0) == 0:
        return {
            "items": [cache_item],
            "total": 1,
            "page": page,
            "limit": limit,
        }

    # 如果缓存有内容，将缓存合并到列表最前面（按 date+type 去重）
    if cache_item:
        items = db_result.get("items", [])
        key_in_db = {(item["date"], item["type"]) for item in items}
        if (cache_item["date"], cache_item["type"]) not in key_in_db:
            items.insert(0, cache_item)
            db_result["items"] = items
            db_result["total"] = (db_result.get("total") or 0) + 1

    return db_result


@router.get("/news/all")
def get_news_all(request: Request):
    """
    一次性返回 latest + hot + history（全部从缓存读取）。
    适用于前端统一拉取三类新闻。
    """
    import time
    t0 = time.perf_counter()
    t_step = t0

    user_id = _get_user_id(request)
    print(f"[news/all] _get_user_id: {round((time.perf_counter()-t_step)*1000,1)}ms")
    t_step = time.perf_counter()

    latest_raw = _load_cached_json(LATEST_CACHE)
    print(f"[news/all] load latest: {round((time.perf_counter()-t_step)*1000,1)}ms")
    t_step = time.perf_counter()

    hot_raw = _load_cached_json(HOT_CACHE)
    print(f"[news/all] load hot: {round((time.perf_counter()-t_step)*1000,1)}ms")
    t_step = time.perf_counter()

    history_raw = _load_cached_json(HISTORY_CACHE)
    print(f"[news/all] load history: {round((time.perf_counter()-t_step)*1000,1)}ms, size={len(history_raw.get('data',[])) if history_raw else 0}")
    t_step = time.perf_counter()

    def _top(result, limit):
        if not result:
            return {"data": [], "count": 0}
        data = result.get("data", [])
        sorted_data = sorted(data, key=lambda x: x.get("importance_score", 0), reverse=True)[:limit]
        return {"data": sorted_data, "count": len(sorted_data)}

    cfg = _load_news_cache_config()
    latest_limit = cfg.get("latestNewsCount", 10)
    result = {
        "latest": _top(latest_raw, latest_limit),
        "hot":   _top(hot_raw, 10),
        "history": _top(history_raw, 50),
    }
    print(f"[news/all] filter all: {round((time.perf_counter()-t_step)*1000,1)}ms")
    print(f"[news/all] TOTAL: {round((time.perf_counter()-t0)*1000,1)}ms")
    return result


@router.get("/news/hot")
def get_news_hot(request: Request):
    """获取热点新闻（当日得分最高的新闻）"""
    result = _load_cached_json(HOT_CACHE)
    if not result:
        return {"data": [], "count": 0}
    data = result.get("data", [])
    sorted_data = sorted(data, key=lambda x: x.get("importance_score", 0), reverse=True)[:10]
    return {"data": sorted_data, "count": len(sorted_data)}


@router.get("/news/latest")
def get_news_latest(request: Request):
    """获取最新批次的高分新闻"""
    result = _load_cached_json(LATEST_CACHE)
    if not result:
        return {"data": [], "count": 0}
    cfg = _load_news_cache_config()
    limit = cfg.get("latestNewsCount", 10)
    data = result.get("data", [])
    sorted_data = sorted(data, key=lambda x: x.get("importance_score", 0), reverse=True)[:limit]
    return {"data": sorted_data, "count": len(sorted_data)}


@router.get("/news/history")
def get_news_history(request: Request, days: int = 3):
    """获取历史新闻"""
    result = _load_cached_json(HISTORY_CACHE)
    if not result:
        return {"data": [], "count": 0}
    data = result.get("data", [])
    sorted_data = sorted(data, key=lambda x: x.get("importance_score", 0), reverse=True)[:50]
    return {"data": sorted_data, "count": len(sorted_data)}


# ============ AI 新闻端点 ============
AI_LATEST_CACHE = _CACHE_DIR / "ai_news_latest.json"
AI_HISTORY_CACHE = _CACHE_DIR / "ai_news_history.json"


@router.get("/news/ai/latest")
def get_ai_news_latest(request: Request):
    """获取 AI 新闻最新缓存"""
    result = _load_cached_json(AI_LATEST_CACHE)
    if not result:
        return {"data": [], "count": 0}
    return {"data": result, "count": len(result)}


@router.get("/news/ai/history")
def get_ai_news_history(request: Request):
    """获取 AI 新闻历史"""
    result = _load_cached_json(AI_HISTORY_CACHE)
    if not result:
        return {"data": [], "count": 0}
    return {"data": result, "count": len(result)}


@router.get("/news/ai/all")
def get_ai_news_all(request: Request):
    """一次性返回 AI 新闻 latest + history（全部从缓存读取）"""
    latest_raw = _load_cached_json(AI_LATEST_CACHE) or []
    history_raw = _load_cached_json(AI_HISTORY_CACHE) or []
    return {
        "latest": {"data": latest_raw, "count": len(latest_raw)},
        "history": {"data": history_raw, "count": len(history_raw)},
    }


@router.get("/news")
def get_news(request: Request):
    """获取最新批次的高分新闻"""
    result = _load_cached_json(LATEST_CACHE)
    if not result:
        return {"data": [], "count": 0}
    data = result.get("data", [])
    sorted_data = sorted(data, key=lambda x: x.get("importance_score", 0), reverse=True)[:10]
    return {"data": sorted_data, "count": len(sorted_data)}


@router.get("/news/detail/{news_id}")
def get_news_detail(news_id: int, request: Request):
    """获取单条新闻详情"""
    news = NewsService.get_news_detail(news_id)
    if not news:
        raise HTTPException(status_code=404, detail="News not found")
    return news


@router.get("/news/list")
def get_news_list(request: Request, page: int = 1, limit: int = 20,
                  source_name: str | None = None,
                  title: str | None = None, summary: str | None = None):
    """
    新闻管理分页列表（管理员）。
    支持按 source_name、title、summary 过滤。
    """
    # 构建 WHERE 子句
    conditions = ["i.source_name IS NOT NULL"]
    params: tuple = ()

    if source_name:
        conditions.append("i.source_name LIKE ?")
        params = (*params, f"%{source_name}%")
    if title:
        conditions.append("i.title LIKE ?")
        params = (*params, f"%{title}%")
    if summary:
        conditions.append("i.summary LIKE ?")
        params = (*params, f"%{summary}%")

    where_clause = " AND ".join(conditions)

    # 使用 script.db 模块查询
    from script.db import query_news_admin
    items, total = query_news_admin(where_clause, params, page, limit)

    return {"list": items, "total": total, "page": page, "limit": limit}


@router.get("/news/primary_sources")
def get_primary_sources_list(request: Request, page: int = 1, limit: int = 20,
                             status: str | None = None, source_name: str | None = None,
                             title: str | None = None):
    """
    新闻管理分页列表（仅 primary_sources，按抓取时间降序）。
    支持按 status、source_name、title 过滤。
    """
    # 构建 WHERE 子句
    conditions = ["source_name IS NOT NULL"]
    params: tuple = ()

    if status:
        conditions.append("status = ?")
        params = (*params, status)
    if source_name:
        conditions.append("source_name LIKE ?")
        params = (*params, f"%{source_name}%")
    if title:
        conditions.append("title LIKE ?")
        params = (*params, f"%{title}%")

    where_clause = " AND ".join(conditions)

    from script.db import query_primary_sources_admin
    items, total = query_primary_sources_admin(where_clause, params, page, limit)

    return {"list": items, "total": total, "page": page, "limit": limit}


@router.post("/news/mark_useful")
def mark_news_useful(request: Request, id: int, useful: bool):
    """
    标记新闻为有用(true)或无用(false)。
    """
    from script.db import get_news_source_name
    source_name = get_news_source_name(id)
    if not source_name:
        raise HTTPException(status_code=404, detail="新闻不存在")

    _mark_useful(id, 1 if useful else -1)
    return {"ok": True, "id": id, "is_useful": 1 if useful else -1}


@router.get("/news/learn")
def learn_news_source(request: Request, url: str, name: str = "", headline: str = "", skip_article: bool = False, force_relearn: bool = False):
    """
    统一的学习接口：通过 URL 学习新闻源配置。

    使用统一的发现流程：
    1. crawl4ai 抓取列表页
    2. 清洗 HTML + 检测 API
    3. API 检测到 → LLM 分析 API 配置
    4. 未检测到 API → LLM DOM 分析
    5.提取样本新闻 + 学习正文配置
    6. 保存到数据库

    保存的 HTML 到 logs/<date>/learning/ 目录。
    """
    from script.discovery import learn_source_config

    if not url:
        raise HTTPException(status_code=400, detail="url 参数必填")

    source_name = name or url
    result = learn_source_config(
        url=url,
        name=source_name,
        headline=headline,
        skip_article_crawler=skip_article,
        force_relearn=force_relearn,
    )

    if not result:
        raise HTTPException(status_code=500, detail="学习失败")

    return {
        "ok": True,
        "name": result.get("name"),
        "source_type": result.get("source_type"),
        "discovery_method": result.get("discovery_method"),
        "list_config": result.get("list_config"),
        "content_extract": result.get("content_extract"),
        "sample_news": result.get("sample_news", []),
    }


@router.get("/news/learn_async")
def learn_news_source_async(request: Request, url: str, name: str = "", headline: str = "", skip_article: bool = False, news_type: str = "stock"):
    """
    异步学习接口：立即返回，后台执行学习。

    force_relearn 固定为 True：覆盖已有配置（包括 content_extract 空 selector 的旧坏数据）。
    """
    import threading
    from script.discovery import learn_source_config

    if not url:
        raise HTTPException(status_code=400, detail="url 参数必填")

    source_name = name or url

    def _run():
        from script.db.db_selector import ensure_db
        ensure_db(news_type)
        try:
            learn_source_config(
                url=url,
                name=source_name,
                headline=headline,
                skip_article_crawler=skip_article,
                force_relearn=True,
            )
        except Exception as e:
            print(f"Async learn failed for {url}: {e}")

    threading.Thread(target=_run, daemon=True).start()
    return {"ok": True, "message": f"学习任务已启动：{source_name}"}


@router.get("/news/fetch")
async def fetch_news_by_url(request: Request, url: str, limit: int = 10, news_type: str = "stock"):
    """
    通过已学习的数据源 URL 获取新闻列表。
    复用 list_crawler 的提取逻辑，不入库。
    """
    from script.log import log as _log
    from script.db.db_selector import ensure_db

    ensure_db(news_type)

    _log("fetch", f"[Fetch] 开始抓取: {url}, limit={limit}")

    from script.db.sources_db import get_crawl_config_by_url
    from script.common.jsonutil import parse_json_field
    from script.crawl.news_list.html_list import extract_list_articles
    from script.crawl.news_list.api_list import fetch_api_items
    from script.discovery.util.html_fetch import fetch_list_html as _fetch_list_html_async

    # 查找数据源配置（从 source_crawl_configs 表）
    src = get_crawl_config_by_url(url)
    if not src:
        _log("fetch", f"[Fetch] 数据源未学习: {url}")
        raise HTTPException(status_code=404, detail="该数据源未学习，请先调用 /api/news/learn")

    list_config_str = src.get("list_config")
    list_config = parse_json_field(list_config_str) if list_config_str else {}
    source_type = src.get("source_type") or list_config.get("type", "")
    source_name = src.get("name") or url

    _log("fetch", f"[Fetch] 数据源: {source_name}, 类型: {source_type or 'html'}")

    news_items = []

    if source_type == "raw":
        # Raw 类型：解析嵌入式 JSON
        from script.discovery.raw_fetch import fetch_raw_html
        from script.discovery.embedded_json import find_embedded_json, extract_news_items
        _log("fetch", f"[Fetch] Raw类型抓取: {url}")
        raw_html = fetch_raw_html(url)
        if not raw_html:
            _log("fetch", f"[Fetch] Raw抓取失败，HTML为空")
            raise HTTPException(status_code=500, detail="页面抓取失败")

        json_data = find_embedded_json(raw_html)
        if not json_data:
            _log("fetch", f"[Fetch] Raw解析失败，未找到嵌入式JSON")
            raise HTTPException(status_code=500, detail="页面嵌入式JSON解析失败")

        # 诊断：检查JSON结构是否匹配配置的字段
        url_field = list_config.get("url_field", "url")
        title_field = list_config.get("title_field", "title")
        _log("fetch", f"[Fetch] Raw JSON类型: {type(json_data).__name__}, 期望字段: url={url_field}, title={title_field}")

        if isinstance(json_data, dict):
            # 检测是否为JS渲染框架的空壳数据（如Next.js __NEXT_DATA__）
            if "props" in json_data or "pageProps" in json_data:
                _log("fetch", f"[Fetch] Raw警告: JSON来自JS渲染框架(Next.js)，内容可能为空，建议改用html类型")
            # 检查配置的字段是否存在
            first_level_keys = list(json_data.keys())[:10]
            _log("fetch", f"[Fetch] Raw JSON顶层keys: {first_level_keys}")

        news_items = extract_news_items(
            json_data,
            url_field=url_field,
            title_field=title_field,
            time_field=list_config.get("time_field", "createTime"),
            summary_field=list_config.get("summary_field", "summary"),
            date_format=list_config.get("date_format"),
        )
        _log("fetch", f"[Fetch] Raw解析完成，获取 {len(news_items)} 条")
    elif source_type == "api":
        # API 类型：调用 API（不写入数据库）
        _log("fetch", f"[Fetch] API类型抓取: {url}")
        news_items = fetch_api_items(src)
        _log("fetch", f"[Fetch] API获取 {len(news_items)} 条")
    else:
        # HTML 类型：使用 list_crawler 的提取逻辑
        # 统一走 fetch_list_html 入口，自动处理 JS 动态渲染
        _log("fetch", f"[Fetch] HTML类型抓取: {url}")
        _, html, markdown = await _fetch_list_html_async(url, return_markdown=True)

        if not html:
            _log("fetch", f"[Fetch] HTML抓取失败: {url}")
            raise HTTPException(status_code=500, detail="页面抓取失败")

        name = src.get("name") or url
        _log("fetch", f"[Fetch] HTML提取配置: {list_config.get('type')}, list_complete={list_config.get('list_complete')}")
        news_items = extract_list_articles(html, markdown, name, list_config, url)
        _log("fetch", f"[Fetch] HTML解析获取 {len(news_items)} 条")

    if not news_items:
        _log("fetch", f"[Fetch] 未获取到任何新闻: {url}, 类型={source_type}")
        if source_type == "raw":
            raise HTTPException(status_code=404, detail="Raw类型解析结果为空，可能需要重新学习并选用html类型")
        raise HTTPException(status_code=404, detail="未获取到新闻，请检查数据源配置")

    # 按 list_crawler 格式输出每条新闻
    for item in news_items:
        title = (item.get("title") or "")[:40]
        pub_time = item.get("time") or item.get("publish_time") or ""
        if title:
            _log("fetch", f"  -> {title}... [OK] {pub_time}")

    _log("fetch", f"[Fetch] 完成: {url}, 共 {len(news_items)} 条")

    return {
        "ok": True,
        "source_name": src.get("name"),
        "source_type": source_type or "html",
        "count": len(news_items),
        "news": news_items[:limit],
    }


@router.get("/news/fetch_async")
def fetch_news_async(request: Request, url: str, limit: int = 10, news_type: str = "stock"):
    """
    异步抓取接口：立即返回，后台执行抓取。
    """
    import threading
    from script.db.sources_db import get_crawl_config_by_url
    from script.discovery.raw_fetch import fetch_raw_html
    from script.discovery.embedded_json import find_embedded_json, extract_news_items
    from script.crawl.news_list.html_list import extract_article_links_with_dates

    def _run():
        from script.db.db_selector import ensure_db
        ensure_db(news_type)
        try:
            src = get_crawl_config_by_url(url)
            if not src:
                print(f"Async fetch failed: {url} not learned")
                return

            list_config_str = src.get("list_config")
            list_config = parse_json_field(list_config_str) if list_config_str else {}
            source_type = src.get("source_type")
            news_items = []

            if source_type == "api" or list_config.get("type") == "api":
                from script.crawl.news_list.api_list import crawl_api_source
                result = crawl_api_source({"url": url}, 0, "")
                if result:
                    news_items = result.get("items", [])
            elif source_type == "raw" or list_config.get("type") == "raw":
                raw_html = fetch_raw_html(url)
                if raw_html:
                    json_data = find_embedded_json(raw_html)
                    if json_data:
                        news_items = extract_news_items(json_data, url)
            else:
                from script.discovery.util.html_fetch import fetch_list_html
                import asyncio
                # 修复 unpacking bug：fetch_list_html 返回 (url, html, markdown)，
                # 不是 (markdown, html)。原代码把 url 误赋给 markdown，导致 if html and markdown 必真
                # 但实际 markdown 变量里是 URL 字符串
                _, html, markdown = asyncio.run(
                    fetch_list_html(url, return_markdown=True)
                )
                if markdown:
                    news_items = extract_article_links_with_dates(markdown, src.get("name") or url)

            print(f"Async fetch completed for {url}: {len(news_items)} items")
        except Exception as e:
            print(f"Async fetch failed for {url}: {e}")

    threading.Thread(target=_run, daemon=True).start()
    return {"ok": True, "message": f"抓取任务已启动：{url}"}


@router.get("/news/article")
def fetch_article_content(request: Request, url: str, source_name: str = ""):
    """
    获取文章正文内容，复用 article_crawler 的抓取逻辑。

    优化：优先使用轻量级抓取（fetch_raw_html + CSS选择器），失败时回退到 crawl4ai。
    """
    from script.db.sources_db import get_content_extract_config
    from script.discovery.html_cleaner import clean_article_html
    from script.discovery.raw_fetch import fetch_raw_html
    from bs4 import BeautifulSoup

    if not url:
        raise HTTPException(status_code=400, detail="url 参数必填")

    # 获取数据源的 content_extract 配置
    content_cfg = None
    if source_name:
        content_cfg = get_content_extract_config(source_name)
        if content_cfg is None:
            raise HTTPException(status_code=404, detail=f"数据源未找到或未配置 content_extract: {source_name}")

    # 优先使用轻量级抓取（静态 HTML + CSS 选择器）
    raw_html = fetch_raw_html(url, timeout=15)
    if raw_html:
        # Step 1: 从原始 HTML 提取发布时间（time_selector 在原始结构上最可靠）
        publish_date = ""
        time_selector = content_cfg.get("time_selector") if content_cfg else None
        if time_selector:
            soup = BeautifulSoup(raw_html, 'html.parser')
            time_el = soup.select_one(time_selector)
            if time_el:
                from script.common.datetimeutil import extract_time_text_from_element
                publish_date = extract_time_text_from_element(time_el)

        # Step 2: 复用 clean_article_html 对整页 HTML 走"移除 nav/header/footer/aside +
        #         找主区 + _prune_soup 短文本元素"链路，再从清洗后 HTML 提取正文。
        #         不要自己生成清理逻辑——直接调现有函数。
        cleaned_html = clean_article_html(raw_html)
        content = _extract_text_from_cleaned(cleaned_html)

        if content and len(content) >= 30:
            return {
                "ok": True,
                "url": url,
                "title": "",
                "publish_date": publish_date,
                "content": content,
                "content_length": len(content),
                "method": "fast",
            }

    # 回退到 crawl4ai JS 渲染
    return _fetch_article_with_crawl4ai(url, source_name, content_cfg)


@router.get("/news/url-preview")
def preview_url_content(request: Request, url: str):
    """
    预览 URL 对应的文章内容，后端代理抓取避免跨域。
    优先轻量抓取，失败回退到 crawl4ai JS 渲染。
    """
    from script.discovery.raw_fetch import fetch_raw_html
    from script.discovery.html_cleaner import clean_article_html
    from bs4 import BeautifulSoup

    if not url:
        raise HTTPException(status_code=400, detail="url 参数必填")

    # 尝试轻量抓取
    raw_html = fetch_raw_html(url, timeout=15)
    if raw_html:
        cleaned_html = clean_article_html(raw_html)
        content = _extract_text_from_cleaned(cleaned_html)
        if content and len(content) >= 30:
            return {
                "ok": True,
                "url": url,
                "content": content,
                "content_length": len(content),
                "method": "fast",
            }

    # 回退到 crawl4ai
    return _fetch_article_with_crawl4ai(url, "", None)


# 元信息行关键词：来源/发布时间/浏览次数/作者/编辑/出处/稿件来源
# 这些信息已经从 time_selector 单独提取到 publish_date 字段，不应再出现在 content 里
_META_KW_RE = re.compile(r'(来源|发布时间|浏览次数|作者|编辑|出处|稿件来源)\s*[:：]')


def _extract_text_from_cleaned(cleaned_html: str) -> str:
    """
    从 clean_article_html 输出中提取纯文本正文。

    clean_article_html 把"含 title+time 的最小容器"放在 <body> 直接子元素里，
    该容器内已是剪枝后的正文段落（含 <p>/<h*> 等）。直接取 body 文本即可。

    后处理：剔除元信息行（来源/发布时间/浏览次数 等）—— 它们已经在 publish_date
    字段中输出，不应再混在 content 里。仅剔除长度 < 100 字符的短行，避免误伤正文
    中"来源"、"作者"等引用。
    """
    from bs4 import BeautifulSoup
    if not cleaned_html:
        return ""
    soup = BeautifulSoup(cleaned_html, 'html.parser')
    body = soup.find('body') or soup
    text = body.get_text(separator="\n", strip=True)

    # 剔除元信息短行
    lines = text.split("\n")
    kept = []
    for line in lines:
        s = line.strip()
        if not s:
            continue
        if len(s) < 100 and _META_KW_RE.search(s):
            continue
        kept.append(s)
    text = "\n".join(kept)

    # 复用现有的中文行过滤，去掉纯英文/URL 等残留 + 子串去重
    text = _filter_chinese_text(text)

    # 剔除末尾的免责声明和风险提示（按行从后向前匹配）
    text = _strip_trailing_disclaimer(text)

    return text


# 中文字符范围（CJK 基本区）
_CHINESE_RE = re.compile(r'[一-鿿]')

# 免责声明和风险提示行模式（从末尾向前逐行匹配，命中即剔除）
# 兼容 "（免责声明：...）" 和 "风险提示：..." 等各种包裹格式
_DISCLAIMER_RE = re.compile(
    r'^(\(|（)?(投资有风险|股市有风险|入市需谨慎|风险提示|免责条款|免责声明|'
    r'Disclaimer|本文仅供参考|不构成投资建议|据此操作风险自担|'
    r'市场有风险投资需谨慎|证券投资咨询服务提供).*',
    re.IGNORECASE,
)


def _strip_trailing_disclaimer(text: str) -> str:
    """从文本末尾向前剔除匹配免责声明/风险提示的行"""
    if not text:
        return text
    lines = text.split("\n")
    # 从后向前跳过匹配的免责行
    end = len(lines)
    while end > 0 and _DISCLAIMER_RE.match(lines[end - 1].strip()):
        end -= 1
    if end < len(lines):
        return "\n".join(lines[:end]).strip()
    return text


def _filter_chinese_text(text: str) -> str:
    """
    过滤文本：保留中文文字内容（含中文标点），过滤掉纯英文、URL、纯符号等"其它类型"。

    规则：
    - 保留所有包含中文字符的行（包括摘要、标题、引文等）
    - 过滤掉完全不含中文字符的行（如导航、URL、纯英文版权信息等）
    - 子串去重：如果新行（去空白后）是已保留某行（去空白后）的子串，跳过
      （解决"标题+元信息行"与"元信息单字段行"重复出现的问题，
      如 "发布时间：来源：xxx  浏览次数：N  发布时间：T" 与单独
      "来源：xxx"、"浏览次数：N  发布时间：T" 同行时只保留前者）
    - 合并连续空行
    """
    if not text:
        return ""
    _WS_RE = re.compile(r'\s+')
    lines = text.split("\n")
    kept = []            # 原始字符串
    kept_compact = []    # 去全部空白后的字符串（用于子串检测）
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if not _CHINESE_RE.search(stripped):
            continue
        compact = _WS_RE.sub('', stripped)
        # 子串去重（基于去空白后的字符串比较，规避空格差异）
        if any(compact in kc for kc in kept_compact):
            continue
        kept.append(stripped)
        kept_compact.append(compact)
    return "\n".join(kept).strip()


def _fetch_article_with_crawl4ai(url: str, source_name: str, content_cfg: dict | None):
    """使用 crawl4ai 获取文章正文（回退方案）"""
    from bs4 import BeautifulSoup
    from script.discovery.html_cleaner import clean_article_html
    from script.discovery.util.html_fetch import fetch_article_html

    import asyncio
    try:
        _, html, _ = asyncio.run(
            fetch_article_html(url, return_markdown=True)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"页面抓取失败: {e}")

    if not html:
        raise HTTPException(status_code=500, detail="页面抓取失败")

    publish_date = ""
    if content_cfg:
        # Step 1: 从原始 HTML 提取发布时间
        time_selector = content_cfg.get("time_selector")
        if time_selector:
            soup = BeautifulSoup(html, 'html.parser')
            time_el = soup.select_one(time_selector)
            if time_el:
                from script.common.datetimeutil import extract_time_text_from_element
                publish_date = extract_time_text_from_element(time_el)

    # Step 2: 复用 clean_article_html 整页清洗（移除 nav/footer/aside + 找主区 +
    #         _prune_soup 短文本元素），再从清洗后 HTML 提取正文。
    cleaned_html = clean_article_html(html)
    content = _extract_text_from_cleaned(cleaned_html)

    return {
        "ok": True,
        "url": url,
        "title": "",
        "publish_date": publish_date,
        "content": content,
        "content_length": len(content),
        "method": "crawl4ai",
    }


def update_news_cache():
    """更新新闻缓存（在新闻采集完成后调用）"""
    return NewsService.update_cache()


# ============ Pipeline Steps ============

_PIPELINE_STEPS = {
    1: ("list_crawler", "采集新闻列表", "list_crawler"),
    2: ("news_filter", "LLM过滤", "news_filter"),
    3: ("article_crawler", "采集文章正文", "article_crawler"),
    4: ("scorer", "LLM评分", "scorer"),
    5: ("findStocks", "核心标的发现", "find_stocks"),
    6: ("sync_sector_values", "同步板块指数", "sync_sector_values"),
    7: ("update_cache", "更新新闻缓存", "update_cache"),
    8: ("hot_news", "热点新闻简报", "hot_news"),
}


@router.post("/news/pipeline/run")
def run_pipeline_full(request: Request):
    """
    触发新闻流水线完整流程（异步，后台执行）：step 1 → 最后一步。
    """
    def _run():
        from service.news_pipeline import run_pipeline
        run_pipeline(start_step=1, end_step=None)

    import threading
    threading.Thread(target=_run, daemon=True).start()
    return {"ok": True, "message": "完整流程已触发"}


@router.post("/news/pipeline/step")
def run_pipeline_step(request: Request, step: int = Query(..., ge=1, le=8)):
    """
    触发单个 Pipeline 步骤（异步，后台执行）。
    step: 1-8 对应各个步骤
    """
    if step not in _PIPELINE_STEPS:
        raise HTTPException(status_code=400, detail=f"无效步骤，有效值：1-8")

    name, desc, log_name = _PIPELINE_STEPS[step]

    def _run():
        from service.news_pipeline import run_pipeline
        run_pipeline(start_step=step, end_step=step)

    import threading
    threading.Thread(target=_run, daemon=True).start()

    return {"ok": True, "step": step, "name": name, "desc": desc, "message": f"Step {step} 已触发"}


# ---------------------------------------------------------------------------
# 异动消息 Pipeline
# ---------------------------------------------------------------------------

_PIPELINE_NEWS_STEPS = {
    1: ("fetch_anomalies",   "采集异动消息",   "anomaly_fetcher"),
    2: ("crawl_contents",   "采集文章正文",   "anomaly_fetcher"),
    3: ("confirm_sources",  "确认数据源",     "confirm_anomaly"),
    4: ("generate_summary", "生成异动简报",   "anomaly_summary"),
}


@router.post("/news/anomaly-pipeline/news/step")
def run_anomaly_news_pipeline_step(request: Request, step: int = Query(..., ge=1, le=4)):
    """触发消息流水线单个步骤（异步，后台执行）。step: 1=采集, 2=抓正文, 3=确认数据源, 4=生成简报"""
    if step not in _PIPELINE_NEWS_STEPS:
        raise HTTPException(status_code=400, detail=f"无效步骤，有效值：1-4")
    name, desc, log_name = _PIPELINE_NEWS_STEPS[step]

    def _run():
        from script.anomaly_news.pipeline import _run_pipeline, PIPELINE_NEWS
        _run_pipeline(PIPELINE_NEWS, "消息流水线", step, step)

    import threading
    threading.Thread(target=_run, daemon=True).start()
    return {"ok": True, "step": step, "name": name, "desc": desc, "message": f"消息流水线 Step {step} 已触发"}


@router.post("/news/anomaly-pipeline/news/run")
def run_anomaly_news_pipeline(request: Request):
    """触发消息流水线完整流程（异步，后台执行）：采集 → 抓正文 → 确认数据源 → 生成简报"""
    def _run():
        from script.log import init_log
        init_log()
        from script.anomaly_news.pipeline import _run_pipeline, PIPELINE_NEWS
        _run_pipeline(PIPELINE_NEWS, "消息流水线")

    import threading
    threading.Thread(target=_run, daemon=True).start()
    return {"ok": True, "message": "消息流水线已触发"}


# ============ 数据源步骤（独立触发 confirm_sources）============

_SOURCE_STEPS = {
    1: ("confirm_sources", "确认数据源", "confirm_anomaly"),
}


@router.post("/news/anomaly-pipeline/source/step")
def run_anomaly_source_pipeline_step(request: Request, step: int = Query(..., ge=1, le=1)):
    """触发数据源步骤（异步，后台执行）。step: 1=确认数据源"""
    if step not in _SOURCE_STEPS:
        raise HTTPException(status_code=400, detail=f"无效步骤，有效值：1")
    name, desc, log_name = _SOURCE_STEPS[step]

    def _run():
        from script.log import init_log
        init_log()
        from script.anomaly_news.pipeline import _run_pipeline, PIPELINE_NEWS
        _run_pipeline(PIPELINE_NEWS, "消息流水线", 2, 2)

    import threading
    threading.Thread(target=_run, daemon=True).start()
    return {"ok": True, "step": step, "name": name, "desc": desc, "message": f"数据源步骤 Step {step} 已触发"}