"""
service/news_stocks.py - 新闻关联股票业务逻辑

组合 db 模块和 api_clients 模块，实现涨跌幅同步等业务功能。
"""

import logging
from datetime import datetime
from script.db import get_recent_stocks, get_recent_stocks_with_created, update_d1_d2_d3_batch
from script.api_clients.iwencai import query_wencai
from script.trading_day import get_trading_day_age, get_trading_day_name

logger = logging.getLogger(__name__)


def sync_news_stocks_change_rates(days: int = 3) -> dict:
    """
    查询最近N天内的新闻关联股票，调用问财获取涨跌幅并批量更新d1/d2/d3字段。

    逻辑：根据每只股票的创建日期计算交易日年龄，决定更新哪个字段
    - 交易日年龄 0 → d1 (发布日)
    - 交易日年龄 1 → d2 (发布后第1个交易日)
    - 交易日年龄 2 → d3 (发布后第2个交易日)

    Args:
        days: 查询天数，默认10天

    Returns:
        {"status": "success"|"error", "updated": dict, "message": str}
    """
    query_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    today = datetime.now().strftime("%Y-%m-%d")

    # 1. 查询最近N天的股票（去重）
    stocks_data = get_recent_stocks(days)
    if not stocks_data:
        logger.info(f"[{query_date}] 涨跌幅同步，无最近{days}天的新闻关联股票")
        return {"status": "success", "updated": {}, "message": "无最近新闻关联股票"}

    all_codes = list(stocks_data.keys())
    logger.info(f"[{query_date}] 涨跌幅同步，查询日期范围{days}天，股票数量: {len(all_codes)}")

    # 2. 分批查询问财（每批最多10个股票）
    batch_size = 10
    change_rates_map: dict[str, str] = {}
    call_count = 0

    for i in range(0, len(all_codes), batch_size):
        batch_codes = all_codes[i:i + batch_size]
        codes_str = ",".join(batch_codes)
        question = f"{codes_str} 最新价, 涨跌幅"
        call_count += 1

        try:
            result = query_wencai(question, secondary_intent="stock")
        except Exception as e:
            logger.error(f"[{query_date}] 涨跌幅同步，问财查询失败: {e}")
            return {"status": "error", "updated": {}, "message": f"问财查询失败: {e}"}

        if result.get("status") != "success":
            logger.error(f"[{query_date}] 涨跌幅同步，问财返回错误: {result.get('message')}")
            return {"status": "error", "updated": {}, "message": result.get("message", "问财返回错误")}

        # 解析结果，去除交易所后缀
        for item in result.get("data", []):
            code = item.get("code", "")
            change_rate = item.get("change_rate", "")
            if code and change_rate:
                normalized_code = code.split(".")[0]
                change_rates_map[normalized_code] = change_rate

    logger.info(f"[{query_date}] 涨跌幅同步，问财接口调用次数: {call_count}，返回数据条数: {len(change_rates_map)}")

    if not change_rates_map:
        logger.error(f"[{query_date}] 涨跌幅同步，问财返回数据为空")
        return {"status": "error", "updated": {}, "message": "问财返回数据为空"}

    # 3. 查询股票及其创建日期，按交易日年龄分组
    stocks_with_created = get_recent_stocks_with_created(days)

    updates = []
    for stock in stocks_with_created:
        code = stock["code"]
        if code not in change_rates_map:
            continue

        rate = change_rates_map[code]
        age = get_trading_day_age(stock["created_at"], today)
        field = get_trading_day_name(age)

        if field:
            updates.append({
                "code": code,
                "created_at": stock["created_at"],
                "field": field,
                "rate": rate,
            })

    # 4. 批量更新（1次SQL）
    updated = update_d1_d2_d3_batch(updates)

    logger.info(f"[{query_date}] 涨跌幅同步，更新记录: d1={updated['d1']}, d2={updated['d2']}, d3={updated['d3']}")
    total = updated['d1'] + updated['d2'] + updated['d3']
    return {"status": "success", "updated": updated, "message": f"更新了 {total} 条记录"}