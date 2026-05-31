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

# 确保 script/common/（有 db/）优先于 top-level common/
_root = Path(__file__).resolve().parent.parent.parent
_script = str(_root / "script")
_stdlib = str(_root)
for p in [_script, _stdlib]:
    if p in sys.path:
        sys.path.remove(p)
sys.path.insert(0, _script)
sys.path.insert(0, _stdlib)

from common.db.connection import get_conn

logger = logging.getLogger(__name__)

# 缓存配置
_CACHE_DIR = Path(__file__).resolve().parent.parent / "cache"
_CACHE_DIR.mkdir(exist_ok=True, parents=True)
LATEST_CACHE = _CACHE_DIR / "news_latest.json"
HISTORY_CACHE = _CACHE_DIR / "news_history.json"
HOT_CACHE = _CACHE_DIR / "news_hot.json"


class NewsService:
    """新闻服务类"""

    @staticmethod
    def query_news(where_clause: str = "", limit: int = 10) -> dict:
        """
        通用新闻查询。排序：分数 DESC，时间 DESC（publish_time）。

        Args:
            where_clause: SQL WHERE 条件（不含 WHERE 关键字）
            limit: 返回条数限制

        Returns:
            包含 data、batch_time、count 的字典
        """
        conn = get_conn()
        try:
            base_sql = """
                SELECT id, title, url, source_name, publish_time, summary,
                       related_sectors, importance_score, reason,
                       publish_sector_values, current_sector_values, created_at
                FROM importance
            """

            if where_clause:
                sql = f"{base_sql} WHERE {where_clause} ORDER BY importance_score DESC, publish_time DESC LIMIT ?"
                rows = conn.execute(sql, (limit,))
            else:
                sql = f"{base_sql} ORDER BY importance_score DESC, publish_time DESC LIMIT ?"
                rows = conn.execute(sql, (limit,))

            data = []
            for row in rows.fetchall():
                related = row[6] or ""
                data.append({
                    "id": row[0],
                    "title": row[1] or "",
                    "url": row[2] or "",
                    "source_name": row[3] or "",
                    "publish_time": row[4],
                    "summary": row[5],
                    "related_sectors": related,
                    "importance_score": row[7],
                    "reason": row[8],
                    "publish_sector_values": row[9],
                    "current_sector_values": row[10],
                    "created_at": row[11],
                    "core_stocks_preview": NewsService._get_core_stocks_preview(related, conn=conn),
                })

            batch_time = data[0]["created_at"] if data else None
            return {"data": data, "batch_time": batch_time, "count": len(data)}
        finally:
            conn.close()

    @staticmethod
    def get_latest_news(limit: int = 10) -> dict:
        """获取最新批次的高分新闻（可能来自缓存）。"""
        cached = NewsService._load_cache(LATEST_CACHE)
        if cached:
            return cached
        result = NewsService.query_news(limit=limit)
        NewsService._save_cache(LATEST_CACHE, result)
        return result

    @staticmethod
    def get_hot_news(limit: int = 10) -> dict:
        """获取当日高分新闻（可能来自缓存）。"""
        cached = NewsService._load_cache(HOT_CACHE)
        if cached:
            return cached
        today = datetime.now().strftime("%Y-%m-%d")
        result = NewsService.query_news(
            where_clause=f"publish_time >= '{today} 00:00:00'",
            limit=limit,
        )
        NewsService._save_cache(HOT_CACHE, result)
        return result

    @staticmethod
    def get_history_news(days: int = 3, limit: int = 50) -> dict:
        """获取历史新闻（可能来自缓存）。"""
        cached = NewsService._load_cache(HISTORY_CACHE)
        if cached:
            return cached
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
        result = NewsService.query_news(
            where_clause=f"publish_time >= '{cutoff}'",
            limit=limit,
        )
        NewsService._save_cache(HISTORY_CACHE, result)
        return result

    @staticmethod
    def get_news_detail(news_id: int) -> Optional[dict]:
        """获取单条新闻详情（含核心标的）。"""
        conn = get_conn()
        try:
            row = conn.execute("""
                SELECT id, title, url, source_name, publish_time, summary,
                       related_sectors, importance_score, reason,
                       publish_sector_values, current_sector_values, created_at
                FROM importance WHERE id = ?
            """, (news_id,)).fetchone()

            if not row:
                return None

            news = {
                "id": row[0], "title": row[1] or "", "url": row[2] or "",
                "source_name": row[3] or "", "publish_time": row[4],
                "summary": row[5], "related_sectors": row[6],
                "importance_score": row[7], "reason": row[8],
                "publish_sector_values": row[9], "current_sector_values": row[10],
                "created_at": row[11],
            }
            related = row[6] or ""
            if related:
                news["core_stocks"] = NewsService._get_core_stocks_preview(related, conn=conn)
            else:
                news["core_stocks"] = []
            return news
        finally:
            conn.close()

    @staticmethod
    def update_cache() -> dict:
        """更新所有缓存。返回 latest/history/hot 的新闻条数。"""
        latest = NewsService.query_news(limit=10)
        NewsService._save_cache(LATEST_CACHE, latest)

        cutoff = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S")
        history = NewsService.query_news(where_clause=f"publish_time >= '{cutoff}'", limit=50)
        NewsService._save_cache(HISTORY_CACHE, history)

        today = datetime.now().strftime("%Y-%m-%d")
        hot = NewsService.query_news(where_clause=f"publish_time >= '{today} 00:00:00'", limit=10)
        NewsService._save_cache(HOT_CACHE, hot)

        return {"latest": latest["count"], "history": history["count"], "hot": hot["count"]}

    @staticmethod
    def _get_core_stocks_preview(related_sectors: str, conn=None) -> list:
        """获取板块关联的核心标的（每板块最多10只）。"""
        if not related_sectors:
            return []

        close_conn = conn is None
        conn = conn or get_conn()
        try:
            sector_list = [s.strip() for s in related_sectors.split("|") if s.strip()]
            if not sector_list:
                return []

            # One query: get top 10 stocks per sector for ALL sectors at once
            placeholders = ",".join("?" * len(sector_list))
            rows = conn.execute(f"""
                SELECT s.code, s.name, s.tier, s.chain_link, s.four_dims, s.moat, s.metrics,
                       r.name as sector
                FROM rag_stocks s
                JOIN rag_sectors r ON s.sector_id = r.id
                WHERE r.name IN ({placeholders})
                ORDER BY r.name, s.tier, s.code
            """, tuple(sector_list)).fetchall()

            stocks = []
            sector_stocks = {}
            for row in rows:
                sector = row[7]
                if sector not in sector_stocks:
                    sector_stocks[sector] = []
                if len(sector_stocks[sector]) < 10:
                    sector_stocks[sector].append({
                        "sector": sector,
                        "code": row[0],
                        "name": row[1],
                        "tier": row[2],
                        "chain_link": row[3],
                        "four_dims": json.loads(row[4]) if row[4] else {},
                        "moat": row[5],
                        "metrics": row[6],
                    })

            # Append in sector-list order (no duplicates)
            for s in sector_list:
                if s in sector_stocks:
                    stocks.extend(sector_stocks[s])
        finally:
            if close_conn:
                conn.close()
        return stocks

    # 兼容别名
    _get_core_stocks_detail = _get_core_stocks_preview

    @staticmethod
    def _save_cache(cache_file: Path, result: dict):
        cache_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def _load_cache(cache_file: Path) -> Optional[dict]:
        if cache_file.exists():
            try:
                return json.loads(cache_file.read_text(encoding="utf-8"))
            except Exception:
                return None
        return None
