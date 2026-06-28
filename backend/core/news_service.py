"""
news_service.py - 新闻服务层

提供新闻数据的业务逻辑，与 API 路由分离。
处理数据查询、缓存管理、核心标的关联等功能。
"""

import json
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

_root = Path(__file__).resolve().parent.parent.parent
_script = str(_root / "script")
_stdlib = str(_root)
for p in [_script, _stdlib]:
    if p in sys.path:
        sys.path.remove(p)
sys.path.insert(0, _script)
sys.path.insert(0, _stdlib)

from script.db import query_news, get_news_by_id
from script.common.jsonutil import write_json, parse_json_field

logger = logging.getLogger(__name__)

_CACHE_DIR = Path(__file__).resolve().parent.parent / "cache"
_CACHE_DIR.mkdir(exist_ok=True, parents=True)
LATEST_CACHE = _CACHE_DIR / "news_latest.json"
HISTORY_CACHE = _CACHE_DIR / "news_history.json"
HOT_CACHE = _CACHE_DIR / "news_hot.json"


class NewsService:
    """新闻服务类"""

    @classmethod
    def _load_news_cache_config(cls) -> dict:
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

    @staticmethod
    def query_news(where_clause: str = "", params: tuple = (), order_by: str = "importance_score DESC, publish_time DESC", limit: int | None = None) -> dict:
        """
        通用新闻查询。排序：分数 DESC，时间 DESC（publish_time）。

        Returns:
            包含 data、batch_time、count 的字典
        """
        data = query_news(where_clause, params, order_by, limit)

        # 优先从 news_stocks 获取新闻关联的核心标的
        news_stocks_map = NewsService._batch_news_stocks([item["id"] for item in data if item.get("id")])
        for item in data:
            importance_id = item.get("id")
            if importance_id and importance_id in news_stocks_map:
                item["core_stocks_preview"] = news_stocks_map[importance_id]
            else:
                item["core_stocks_preview"] = []

        batch_time = data[0]["created_at"] if data else None
        return {"data": data, "batch_time": batch_time, "count": len(data)}

    @staticmethod
    def _batch_news_stocks(news_ids: list[int]) -> dict:
        """批量获取新闻关联的核心标的（从 news_stocks 表）"""
        from script.db.news_stocks import get_batch_by_importance
        return get_batch_by_importance(news_ids)

    @staticmethod
    def get_latest_news() -> dict:
        """获取当日创建的高分新闻（可能来自缓存）。"""
        cached = NewsService._load_cache(LATEST_CACHE)
        # 缓存为空说明缓存文件已损坏或过期，跳过缓存直接查库
        if cached and cached.get("count", 0) > 0:
            return cached
        cfg = NewsService._load_news_cache_config()
        min_score = cfg.get("minScore", 2)
        today = datetime.now().strftime("%Y-%m-%d")
        result = NewsService.query_news(
            where_clause="created_at >= ? AND importance_score >= ?",
            params=(f"{today} 00:00:00", min_score),
        )
        NewsService._save_cache(LATEST_CACHE, result)
        return result

    @staticmethod
    def get_hot_news() -> dict:
        """获取当日热点新闻（分数不低于 hotNewsMinScore，可能来自缓存）。"""
        cached = NewsService._load_cache(HOT_CACHE)
        # 缓存为空说明缓存文件已损坏或过期，跳过缓存直接查库
        if cached and cached.get("count", 0) > 0:
            return cached
        cfg = NewsService._load_news_cache_config()
        hot_min = cfg.get("hotNewsMinScore", 5)
        today = datetime.now().strftime("%Y-%m-%d")
        result = NewsService.query_news(
            where_clause="created_at >= ? AND importance_score >= ?",
            params=(f"{today} 00:00:00", hot_min),
        )
        NewsService._save_cache(HOT_CACHE, result)
        return result

    @staticmethod
    def get_history_news(days: int | None = None) -> dict:
        """获取历史新闻（可能来自缓存）。"""
        cached = NewsService._load_cache(HISTORY_CACHE)
        if cached:
            return cached
        cfg = NewsService._load_news_cache_config()
        days = days if days is not None else cfg.get("historyDays", 3)
        min_score = cfg.get("minScore", 2)
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
        result = NewsService.query_news(
            where_clause="created_at >= ? AND importance_score >= ?",
            params=(cutoff, min_score),
        )
        NewsService._save_cache(HISTORY_CACHE, result)
        return result

    @staticmethod
    def get_news_detail(news_id: int) -> Optional[dict]:
        """获取单条新闻详情（含核心标的）。"""
        news = get_news_by_id(news_id)
        if not news:
            return None
        stocks_map = NewsService._batch_news_stocks([news_id])
        news["core_stocks"] = stocks_map.get(news_id, [])
        return news

    @staticmethod
    def update_cache() -> dict:
        """强制更新所有缓存（直接查库，不走缓存）。返回 latest/history/hot 的新闻条数。"""
        cfg = NewsService._load_news_cache_config()
        min_score = cfg.get("minScore", 2)
        hot_min = cfg.get("hotNewsMinScore", 5)
        today = datetime.now().strftime("%Y-%m-%d")

        # 强制查库，不走缓存逻辑
        latest = NewsService.query_news(
            where_clause="created_at >= ? AND importance_score >= ?",
            params=(f"{today} 00:00:00", min_score),
        )
        NewsService._save_cache(LATEST_CACHE, latest)

        history_days = cfg.get("historyDays", 3)
        cutoff = (datetime.now() - timedelta(days=history_days)).strftime("%Y-%m-%d %H:%M:%S")
        history = NewsService.query_news(
            where_clause="created_at >= ? AND importance_score >= ?",
            params=(cutoff, min_score),
        )
        NewsService._save_cache(HISTORY_CACHE, history)

        hot = NewsService.query_news(
            where_clause="created_at >= ? AND importance_score >= ?",
            params=(f"{today} 00:00:00", hot_min),
        )
        NewsService._save_cache(HOT_CACHE, hot)

        return {"latest": latest["count"], "history": history["count"], "hot": hot["count"]}

    @staticmethod
    def _save_cache(cache_file: Path, result: dict):
        write_json(result, cache_file)

    @staticmethod
    def _load_cache(cache_file: Path) -> Optional[dict]:
        if cache_file.exists():
            try:
                import json
                return json.loads(cache_file.read_text(encoding="utf-8"))
            except Exception:
                return None
        return None

    @staticmethod
    def update_sector_change_rates() -> dict:
        """
        查询所有板块/概念的当前涨跌幅，更新缓存新闻中的 current_sector_values 和 current_sector_change_rates。

        仅在交易时间段执行：周一至周五 9:30-11:30 和 13:00-15:00。

        Returns:
            {"total_sectors": int, "updated_news": int, "cache_files": [str]}
        """
        from datetime import time
        now = datetime.now()
        # 仅工作日执行
        if now.weekday() >= 5:
            logger.info("[SectorChangeRate] 非交易日，跳过")
            return {"total_sectors": 0, "updated_news": 0, "cache_files": []}
        current_time = now.time()
        # 交易时段检查：9:30-11:30 和 13:00-15:00
        morning_start = time(9, 30)
        morning_end = time(11, 30)
        afternoon_start = time(13, 0)
        afternoon_end = time(15, 0)
        in_morning = morning_start <= current_time <= morning_end
        in_afternoon = afternoon_start <= current_time <= afternoon_end
        if not (in_morning or in_afternoon):
            logger.info(f"[SectorChangeRate] 非交易时段（当前 {current_time.strftime('%H:%M')}），跳过")
            return {"total_sectors": 0, "updated_news": 0, "cache_files": []}
        from script.api_clients.iwencai import query_wencai
        from script.db.sectors import normalize

        # 1. 查询同花顺所有板块指数（含涨跌幅）
        result = query_wencai("二级概念板块或二级行业板块，涨跌幅排名，成交额，成交量，大单净流入额/流通市值*10000,上涨家数,下跌家数,涨停家数", secondary_intent="zhishu", loop=5)
        if result["status"] != "success" or not result.get("data"):
            logger.warning(f"[SectorChangeRate] 查询失败: {result.get('message', 'unknown')}")
            return {"total_sectors": 0, "updated_news": 0, "cache_files": []}

        total_sectors = result.get("total_count", 0)

        # 构建 {板块名: (指数值, 涨跌幅)} 字典
        sector_price_map: dict[str, float] = {}
        sector_change_map: dict[str, float] = {}
        for item in result["data"]:
            name = item.get("name", "")
            price = item.get("price")
            change_rate = item.get("change_rate", "")
            if name and price:
                sector_price_map[name] = float(price)
            if name and change_rate:
                try:
                    # change_rate 格式如 "+2.35%" 或 "-1.23%"
                    sector_change_map[name] = float(change_rate.rstrip("%").lstrip("+"))
                except ValueError:
                    pass

        logger.info(f"[SectorChangeRate] 获取到 {len(sector_price_map)}/{total_sectors} 个板块指数（含涨跌幅）")

        # 2. 更新各缓存文件
        cache_files = [LATEST_CACHE, HISTORY_CACHE, HOT_CACHE]
        updated_count = 0

        for cache_file in cache_files:
            cached = NewsService._load_cache(cache_file)
            if not cached or not cached.get("data"):
                continue

            for news in cached["data"]:
                related_sectors = news.get("related_sectors", "")
                if not related_sectors:
                    news["current_sector_values"] = ""
                    news["current_sector_change_rates"] = ""
                    continue

                value_parts = []
                change_parts = []
                for sec in related_sectors.split("|"):
                    sec = sec.strip()
                    if not sec:
                        continue

                    # 归一化匹配
                    matched = normalize(sec)
                    std_name = None
                    for m in matched:
                        if m.get("normalized") and m.get("name"):
                            std_name = m["name"]
                            break

                    # 通过归一化名称查找
                    if std_name:
                        if std_name in sector_price_map:
                            value_parts.append(f"{std_name}:{sector_price_map[std_name]}")
                        if std_name in sector_change_map:
                            change_parts.append(f"{std_name}:{sector_change_map[std_name]}%")
                        # fallback 模糊匹配
                        elif std_name:
                            for idx_name in sector_price_map:
                                if std_name in idx_name or idx_name in std_name:
                                    value_parts.append(f"{idx_name}:{sector_price_map[idx_name]}")
                                    if idx_name in sector_change_map:
                                        change_parts.append(f"{idx_name}:{sector_change_map[idx_name]}%")
                                    break

                news["current_sector_values"] = "|".join(value_parts)
                news["current_sector_change_rates"] = "|".join(change_parts)
                updated_count += 1

            NewsService._save_cache(cache_file, cached)
            logger.info(f"[SectorChangeRate] 已更新 {cache_file.name}: {cached.get('count', 0)} 条新闻")

        # 3. 清理内存
        sector_price_map.clear()
        sector_change_map.clear()

        logger.info(f"[SectorChangeRate] 完成，共更新 {updated_count} 条新闻的板块涨跌幅")
        return {"total_sectors": total_sectors, "updated_news": updated_count, "cache_files": [f.name for f in cache_files]}