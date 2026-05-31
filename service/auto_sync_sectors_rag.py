"""
auto_sync_sectors_rag.py - 同步板块 RAG 内容

功能：
  - 从同花顺获取所有板块列表
  - 调用 LLM 根据核心标的.md 提示词分析每个板块的核心标的
  - 保存到 rag_sectors、rag_stocks 表

使用：
  python service/auto_sync_sectors_rag.py
"""

import sys
from pathlib import Path
from datetime import datetime
import json

_BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BASE_DIR))

from common.db.rag import save_all
from api_clients.iwencai import query_wencai
from llm import call


PROMPT_TEMPLATE = """# 核心标的筛选提示词（精简执行版）

## 角色与目标
你是一位资深产业分析师。请针对【目标板块】系统性筛选核心标的。

## 第一步：全产业链拆解
检查以下环节是否存在：
- 上游资源/原材料
- 中游制造/核心元器件
- 下游封测/应用

## 第二步：四维度评估
对相关A股标的评估：
1. 竞争格局（高/中/低）
2. 盈利质量（高/中/低）
3. 客户壁垒（高/中/低）
4. 技术迭代（高/中/低）

## 第三步：严格剔除
- 官方声明无实质业务
- 间接参股无实际往来
- 关联收入<10%
- 仅送样无量产

## 输出格式（严格JSON）

板块名称：{sector_name}

返回：
{{
  "sector": {{
    "chain_coverage": {{
      "上游": "已覆盖/无此环节",
      "中游": "已覆盖/无此环节",
      "下游": "已覆盖/无此环节"
    }}
  }},
  "stocks": [
    {{
      "code": "代码",
      "name": "名称",
      "tier": "梯队",
      "chain_link": "环节",
      "four_dims": {{"竞":"高/中/低","盈":"高/中/低","客":"高/中/低","技":"高/中/低"}},
      "moat": "护城河",
      "q1_metrics": "Q1业绩",
      "include_path": "A/B/C"
    }}
  ],
  "eliminated": [
    {{"code":"代码","name":"名称","reason":"原因","rule_no":"规则"}}
  ]
}}
"""


def log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def get_all_sectors_from_wencai() -> list[dict]:
    """从同花顺获取所有板块"""
    result = query_wencai("二级概念板块或二级行业板块", secondary_intent="zhishu", page=1, perpage=100, loop=5)
    if result["status"] != "success":
        log(f"获取板块失败: {result.get('message')}")
        return []
    return result.get("data", [])


def analyze_sector(sector_name: str) -> dict | None:
    """调用 LLM 分析板块核心标的"""
    prompt = PROMPT_TEMPLATE.format(sector_name=sector_name)
    try:
        result = call([{"role": "user", "content": prompt}])
        if not result:
            return None
        import re
        m = re.search(r'\{[\s\S]*\}', result)
        if m:
            return json.loads(m.group())
    except Exception as e:
        log(f"  LLM 失败: {e}")
    return None


def sync_sector(sector_name: str) -> bool:
    """同步单个板块 RAG"""
    log(f"分析: {sector_name}")
    parsed = analyze_sector(sector_name)
    if not parsed:
        log(f"  -> 跳过")
        return False
    try:
        save_all(sector_name, json.dumps(parsed, ensure_ascii=False), parsed)
        stocks = len(parsed.get("stocks", []))
        elim = len(parsed.get("eliminated", []))
        log(f"  -> OK: {stocks} 标的, {elim} 剔除")
        return True
    except Exception as e:
        log(f"  -> 保存失败: {e}")
        return False


def run():
    log("=" * 60)
    log("同步板块 RAG 内容")
    log("=" * 60)

    log("获取板块列表...")
    sectors = get_all_sectors_from_wencai()
    log(f"共 {len(sectors)} 个板块")

    if not sectors:
        log("无可用板块")
        return

    ok, fail = 0, 0
    for i, s in enumerate(sectors, 1):
        name = s.get("name", "")
        if not name:
            continue
        log(f"\n[{i}/{len(sectors)}]")
        if sync_sector(name):
            ok += 1
        else:
            fail += 1

    log(f"\n完成: 成功 {ok}, 失败 {fail}")


if __name__ == "__main__":
    run()
