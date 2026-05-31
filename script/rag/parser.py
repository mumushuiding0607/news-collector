"""
rag/parser.py - 核心标的报告解析器

优化备注（2026-05-30）：
  - 每次save_to_db必须重新parse_report，因为核心标的内容会更新，无需缓存

功能：
  - 解析 LLM 生成的报告文本
  - 提取结构化数据入库

使用：
  python -m script.rag.parser --sector "新能源汽车" --report "报告内容"
"""

import re
import sys
import logging
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

from common.db.connection import get_conn
from common.db import rag


def parse_four_dims(dim_str: str) -> dict:
    """解析四维度字符串，如 '高/中/低/高' -> {'竞争': '高', '盈利': '中', '客户': '低', '技术': '高'}"""
    result = {}
    dims = ['竞争', '盈利', '客户', '技术']
    parts = dim_str.split('/')
    logger.debug(f"解析四维度: {dim_str} -> parts: {parts}")
    for i, dim in enumerate(dims):
        result[dim] = parts[i].strip() if i < len(parts) else '未知'
    return result


def extract_stocks_from_table(table_text: str) -> list[dict]:
    """从正文表格提取标的列表"""
    stocks = []
    lines = table_text.strip().split('\n')
    logger.info(f"开始解析正文表格，共 {len(lines)} 行")

    for line in lines:
        line = line.strip()
        if not line or '|' not in line:
            continue

        parts = [p.strip() for p in line.split('|')]
        if len(parts) < 6:
            continue

        # 跳过表头和分隔行
        tier_raw = parts[1].strip()
        tier = tier_raw.replace('*', '')
        if '---' in line or tier in ['梯队', ''] or not tier:
            continue

        # 只接受有效的梯队行（允许 LLM 输出简写，如"第三梯队A"而非"第三梯队A类"）
        tier_variants = {
            '第一梯队', '第二梯队',
            '第三梯队A类', '第三梯队A', '第三梯队B类', '第三梯队B',
        }
        if tier not in tier_variants:
            continue

        try:
            # parts[3] 可能是 "-"（无代码），名称不含 * 但可能含 **bold**
            raw_code = parts[3].strip()
            code = raw_code.replace('*', '') if raw_code not in ('-', '**-**') else ''

            stock = {
                'tier': tier,
                'sort': parts[2].strip(),
                'code': code,
                'name': parts[4].strip().replace('*', ''),
                'chain_link': parts[5].strip(),
                'four_dims': parse_four_dims(parts[6].strip()) if len(parts) > 6 else {},
                'moat': parts[7].strip() if len(parts) > 7 else '',
                'q1_metrics': parts[8].strip() if len(parts) > 8 else '',
                'include_path': parts[9].strip() if len(parts) > 9 else '',
            }
            if not stock['name']:
                continue
            stocks.append(stock)
            logger.debug(f"解析标的: {tier} {stock['code']} {stock['name']}")
        except (IndexError, ValueError) as e:
            logger.warning(f"解析行失败: {line[:50]}... 错误: {e}")
            continue

    logger.info(f"正文表格解析完成，共提取 {len(stocks)} 只标的")
    return stocks


def extract_eliminated_from_text(text: str) -> list[dict]:
    """从附录一提取已剔除标的"""
    eliminated = []

    # 查找附录一表格
    if '附录一' not in text:
        logger.info("未找到附录一，跳过")
        return eliminated

    logger.info("开始解析附录一（已剔除标的）")
    # 提取表格部分
    lines = text.split('\n')
    in_table = False
    for line in lines:
        line = line.strip()

        if '附录一' in line:
            in_table = True
            logger.debug(f"进入附录一表格区域")
            continue

        if in_table:
            # 遇到分隔行（:---|）或附录二标识则退出
            if '---' in line or '附录二' in line:
                break
            if '|' not in line:
                continue

            parts = [p.strip() for p in line.split('|')]
            if len(parts) < 4:
                continue

            # 跳过表头行
            if parts[1].strip() in ('名称', '代码', ''):
                continue

            try:
                elim = {
                    'code': parts[1].strip().replace('*', ''),
                    'name': parts[2].strip().replace('*', ''),
                    'reason': parts[3].strip(),
                    'rule_no': parts[4].strip() if len(parts) > 4 else '',
                }
                eliminated.append(elim)
                logger.debug(f"剔除标的: {elim['code']} {elim['name']} - 规则{elim['rule_no']}")
            except (IndexError, ValueError) as e:
                logger.warning(f"解析剔除行失败: {line[:50]}... 错误: {e}")
                continue

    logger.info(f"附录一解析完成，共 {len(eliminated)} 只已剔除标的")
    return eliminated


def extract_chain_coverage(text: str) -> dict:
    """从附录二提取产业链覆盖情况"""
    coverage = {}

    if '附录二' not in text:
        return coverage

    lines = text.split('\n')
    in_section = False
    for line in lines:
        line = line.strip()

        if '附录二' in line:
            in_section = True
            continue

        if in_section:
            if '附录三' in line or '末尾' in line:
                break
            if ':' in line or '√' in line or '×' in line:
                # 解析环节状态
                for link in ['上游资源', '上游设备', '上游材料', '中游制造', '中游设计',
                           '中游模组', '中游系统', '下游封测', '下游应用']:
                    if link in line:
                        if '已覆盖' in line or '√' in line:
                            # 提取数量
                            match = re.search(r'(\d+)', line)
                            count = match.group(1) if match else '1'
                            coverage[link] = f'已覆盖{count}家'
                        elif '无此环节' in line:
                            coverage[link] = '无此环节'
                        else:
                            coverage[link] = '未覆盖'
    return coverage


def parse_report(sector_name: str, report_text: str) -> dict:
    """
    解析报告文本，返回结构化数据

    Returns:
        {
            'sector': {'name': str, 'chain_coverage': dict},
            'stocks': [list of stock dicts],
            'eliminated': [list of eliminated dicts]
        }
    """
    logger.info(f"=== 开始解析报告: {sector_name} ===")
    logger.info(f"报告长度: {len(report_text)} 字符")

    # 1. 提取正文表格中的标的
    logger.info("Step 1: 提取正文表格")
    stocks = extract_stocks_from_table(report_text)

    # 2. 提取已剔除标的
    logger.info("Step 2: 提取附录一（已剔除标的）")
    eliminated = extract_eliminated_from_text(report_text)

    # 3. 提取产业链覆盖
    logger.info("Step 3: 提取附录二（产业链覆盖）")
    chain_coverage = extract_chain_coverage(report_text)

    logger.info(f"=== 解析完成: {sector_name} - 标的{len(stocks)}只, 剔除{len(eliminated)}只 ===")

    return {
        'sector': {
            'name': sector_name,
            'chain_coverage': chain_coverage
        },
        'stocks': stocks,
        'eliminated': eliminated
    }


def save_to_db(sector_name: str, report_text: str) -> bool:
    """解析报告并保存到数据库（使用 db.rag 层）"""
    try:
        # 解析报告
        parsed = parse_report(sector_name, report_text)
        # 使用 db.rag.save_all 批量保存
        return rag.save_all(sector_name, report_text, parsed)
    except Exception as e:
        logger.error(f"保存失败: {e}")
        return False


def query_stocks(sector_name: str = None, tier: str = None, min_dims: int = 2) -> list[dict]:
    """查询核心标的（使用 db.rag 层）"""
    return rag.query_stocks(sector_name=sector_name, tier=tier, min_high_dims=min_dims)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="核心标的报告解析")
    parser.add_argument("--sector", required=True, help="板块名称")
    parser.add_argument("--report", required=True, help="报告文件路径")
    parser.add_argument("--query", action="store_true", help="查询模式")
    args = parser.parse_args()

    if args.query:
        # 查询模式
        results = query_stocks(args.sector)
        print(f"找到 {len(results)} 只标的:")
        for s in results:
            print(f"  {s['tier']} {s['code']} {s['name']} ({s['four_dims']})")
    else:
        # 解析入库模式
        report_text = Path(args.report).read_text(encoding='utf-8')
        if save_to_db(args.sector, report_text):
            print("解析入库成功!")
        else:
            print("解析入库失败")
            sys.exit(1)