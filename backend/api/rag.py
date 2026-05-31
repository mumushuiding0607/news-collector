"""
RAG API - 核心标的知识库查询
"""
import json
from fastapi import APIRouter
from pydantic import BaseModel

from common.db.connection import get_conn

router = APIRouter(prefix="/rag", tags=["RAG"])


class ParseRequest(BaseModel):
    sector_name: str
    report_text: str


class StockQuery(BaseModel):
    sector_name: str | None = None
    tier: str | None = None
    min_high_dims: int = 2


@router.post("/parse")
def parse_report(req: ParseRequest):
    """解析报告并保存到数据库"""
    from script.rag.parser import save_to_db

    success = save_to_db(req.sector_name, req.report_text)
    return {"success": success, "sector": req.sector_name}


@router.get("/stocks")
def query_stocks(sector: str | None = None, tier: str | None = None, min_dims: int = 2):
    """查询核心标的"""
    conn = get_conn()
    try:
        sql = """
            SELECT s.*, r.name as sector_name
            FROM rag_stocks s
            JOIN rag_sectors r ON s.sector_id = r.id
            WHERE 1=1
        """
        params = []
        if sector:
            sql += " AND r.name = ?"
            params.append(sector)
        if tier:
            sql += " AND s.tier = ?"
            params.append(tier)

        cur = conn.execute(sql, params)
        rows = cur.fetchall()
        stocks = []
        for row in rows:
            four_dims = json.loads(row[6] or '{}')
            high_count = sum(1 for v in four_dims.values() if v == '高')
            if high_count < min_dims:
                continue
            stocks.append({
                'id': row[0], 'sector_id': row[1], 'code': row[2], 'name': row[3],
                'tier': row[4], 'chain_link': row[5], 'four_dims': four_dims,
                'moat': row[7], 'q1_metrics': row[8], 'include_path': row[9],
                'sector_name': row[12],
            })
        return {"count": len(stocks), "stocks": stocks}
    finally:
        conn.close()


@router.get("/sectors")
def list_sectors():
    """查询所有板块"""
    conn = get_conn()
    try:
        cur = conn.execute("""
            SELECT r.id, r.name, r.chain_structure,
                   COUNT(s.id) as stock_count,
                   COUNT(e.id) as eliminated_count
            FROM rag_sectors r
            LEFT JOIN rag_stocks s ON r.id = s.sector_id
            LEFT JOIN rag_eliminated e ON r.id = e.sector_id
            GROUP BY r.id
        """)
        rows = cur.fetchall()
        sectors = []
        for row in rows:
            chain = json.loads(row[2] or '{}') if row[2] else {}
            sectors.append({
                'id': row[0], 'name': row[1], 'chain_structure': chain,
                'stock_count': row[3], 'eliminated_count': row[4],
            })
        return {"count": len(sectors), "sectors": sectors}
    finally:
        conn.close()


@router.get("/stocks/by-sector/{sector_name}")
def get_stocks_by_sector(sector_name: str, tier: str | None = None):
    """按板块名称查询核心标的"""
    conn = get_conn()
    try:
        sql = """
            SELECT s.*, r.name as sector_name
            FROM rag_stocks s
            JOIN rag_sectors r ON s.sector_id = r.id
            WHERE r.name = ?
        """
        params = [sector_name]
        if tier:
            sql += " AND s.tier = ?"
            params.append(tier)
        cur = conn.execute(sql, params)
        rows = cur.fetchall()
        stocks = []
        for row in rows:
            four_dims = json.loads(row[6] or '{}')
            stocks.append({
                'id': row[0], 'sector_id': row[1], 'code': row[2], 'name': row[3],
                'tier': row[4], 'chain_link': row[5], 'four_dims': four_dims,
                'moat': row[7], 'q1_metrics': row[8], 'include_path': row[9],
                'sector_name': row[12],
            })
        return {"count": len(stocks), "stocks": stocks}
    finally:
        conn.close()
