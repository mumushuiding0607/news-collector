"""
report.py - 新闻评分与关联板块报告模块

功能：
  - 查询最新一批评分的新闻（前10名）
  - 批量查询关联板块当前涨跌幅
  - 计算新闻发布至今的涨跌幅
  - 生成格式化报告

使用：
  python report.py
  python report.py --top 5
"""

import json
from datetime import datetime
from pathlib import Path

from common.db import get_recent_by_score
from common.db.sectors import normalize
from sector.sector_index import batch_query_sectors, query_sector_index, ensure_sector_indices_table


# ==================== 报告生成 ====================

def generate_report(top_n: int = 10) -> dict:
    """
    生成新闻评分与关联板块报告

    Args:
        top_n: 返回前N条高评分新闻（默认10）

    Returns:
        {
            "generated_at": "2026-05-28 15:30:00",
            "batch_info": "2026-05-28 14:00:00 ~ 15:00:00",
            "top_news": [
                {
                    "rank": 1,
                    "news_id": 123,
                    "title": "...",
                    "score": 8,
                    "sectors": ["稀土", "芯片"],
                    "sector_data": [
                        {"name": "稀土永磁", "change_rate": "+2.35%", ...}
                    ],
                    "change_since_publish": "+1.2%"
                },
                ...
            ]
        }
    """
    ensure_sector_indices_table()

    # 读取高评分新闻
    news_list = get_recent_by_score(min_score=1, limit=top_n)
    if not news_list:
        return {"status": "error", "message": "没有评分新闻"}

    top_news = []
    for rank, row in enumerate(news_list, 1):
        (
            id, news_id, source_name, title, url, publish_time,
            summary, related_sectors, importance_score, reason, created_at
        ) = row

        # 解析关联板块
        sector_names = []
        if related_sectors:
            # related_sectors 格式可能是 "稀土|芯片" 或 "稀土,芯片"
            sep = "|" if "|" in related_sectors else ","
            sector_names = [s.strip() for s in related_sectors.split(sep) if s.strip()]

        # 归一化板块名并批量查询
        sector_data = []
        if sector_names:
            normalized = normalize("|".join(sector_names))
            for n in normalized:
                if n.get("normalized") and n.get("code"):
                    idx = query_sector_index(n["name"])
                    if idx:
                        sector_data.append(idx)

        # 计算综合涨跌幅
        change_since_publish = calculate_change_since_publish(sector_data, publish_time)

        top_news.append({
            "rank": rank,
            "news_id": news_id,
            "id": id,
            "title": title,
            "url": url,
            "source": source_name,
            "publish_time": publish_time,
            "score": importance_score,
            "summary": summary,
            "reason": reason,
            "sectors": sector_names,
            "sector_data": sector_data,
            "change_since_publish": change_since_publish,
        })

    return {
        "status": "success",
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "top_news": top_news,
    }


def calculate_change_since_publish(sector_data: list[dict], publish_time: str) -> str:
    """
    计算新闻发布至今的综合涨跌幅

    Args:
        sector_data: 板块指数列表
        publish_time: 新闻发布时间

    Returns:
        "+2.35%" 或 "-1.2%" 或 "N/A"
    """
    if not sector_data or not publish_time:
        return "N/A"

    rates = []
    for sector in sector_data:
        change_rate = sector.get("change_rate", "")
        if change_rate:
            try:
                # "+2.35%" -> 2.35
                rate = float(change_rate.rstrip("%").lstrip("+"))
                rates.append(rate)
            except ValueError:
                pass

    if not rates:
        return "N/A"

    # 取平均值
    avg = sum(rates) / len(rates)
    sign = "+" if avg > 0 else ""
    return f"{sign}{avg:.2f}%"


def format_report(report: dict) -> str:
    """将报告字典格式化为可读文本"""
    if report["status"] != "success":
        return f"错误: {report.get('message', '未知错误')}"

    lines = []
    lines.append("=" * 70)
    lines.append(f"新闻采集分析报告 - {report['generated_at']}")
    lines.append("=" * 70)

    for news in report["top_news"]:
        lines.append("")
        lines.append(f"【{news['rank']}】{news['title'][:50]}")
        lines.append(f"  来源: {news['source']} | 时间: {news['publish_time']}")
        lines.append(f"  评分: {news['score']} 分")
        lines.append(f"  摘要: {news['summary'][:80]}..." if news.get("summary") and len(news.get("summary", "")) > 80 else f"  摘要: {news.get('summary', 'N/A')}")
        lines.append(f"  关联板块: {', '.join(news['sectors']) if news['sectors'] else 'N/A'}")
        lines.append(f"  发布至今涨跌幅: {news['change_since_publish']}")

        if news.get("sector_data"):
            lines.append("  板块详情:")
            for s in news["sector_data"]:
                lines.append(f"    - {s['name']}: {s['change_rate']} | 换手: {s.get('turnover', 'N/A')}%")

        lines.append(f"  理由: {news.get('reason', 'N/A')}")

    lines.append("")
    lines.append("=" * 70)
    lines.append(f"共 {len(report['top_news'])} 条高评分新闻")

    return "\n".join(lines)


# ==================== CLI入口 ====================

def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description="新闻评分报告生成")
    parser.add_argument("--top", type=int, default=10, help="返回前N条（默认10）")
    parser.add_argument("--json", action="store_true", help="输出JSON格式")
    parser.add_argument("--save", type=str, metavar="FILE", help="保存到文件")
    args = parser.parse_args()

    report = generate_report(top_n=args.top)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(format_report(report))

    if args.save:
        with open(args.save, "w", encoding="utf-8") as f:
            f.write(format_report(report))
        print(f"\n报告已保存到: {args.save}")


if __name__ == "__main__":
    main()