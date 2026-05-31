"""
evaluator.py - 新闻评分回测工作流脚本

每次调用 LLM 分析某条新闻的所有评论，工作流三步：
1. 收集过滤：汇总评论、过滤非建设性/无关内容
2. 关联判断：判断有效评论与新闻的关联程度
3. 优化建议：结合新闻与评论生成评分优化建议

使用方式:
    python -m script.backtest.evaluator --days 7      # 回测最近7天
    python -m script.backtest.evaluator --news-id 123   # 回测单条新闻
"""

import sys
import json
import re
import argparse
from datetime import datetime, timedelta
from pathlib import Path

# 添加项目路径
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "script"))

from common.db.connection import get_conn

# 提示词文件路径
PROMPT_FILE = BASE_DIR / "prompt" / "评分回测.md"


def _load_prompt() -> str:
    """从提示词文件加载正文"""
    if PROMPT_FILE.exists():
        content = PROMPT_FILE.read_text(encoding="utf-8")
        # 提取 ```python 或 ``` 代码块
        m = re.search(r"```(?:python)?([\s\S]+?)```", content)
        if m:
            return m.group(1).strip()
        return content.strip()
    return _FALLBACK_PROMPT


_FALLBACK_PROMPT = """你是新闻评分回测专家。工作流：

1. 收集过滤：汇总所有评论，过滤非建设性意见、无关内容、无法帮助优化的内容
2. 关联判断：判断有效评论与新闻的关联程度（强相关/弱相关/不相关）
3. 优化建议：结合新闻与评论提出优化建议

新闻：{title}（{score}分）
板块：{sectors}
摘要：{summary}
推荐逻辑：{reason}
评论列表：
{comments}

以JSON返回：
{{"news_id":{news_id},"有效评论":[{{"评论内容":"","保留原因":"","关联程度":""}}],"优化建议":[{{"类别":"","问题":"","建议":""}}]}}
"""


def build_prompt(news: dict, comments: list) -> str:
    """填充提示词占位符"""
    template = _load_prompt()

    news_id = news.get("id") or 0
    title = news.get("title") or ""
    score = str(news.get("importance_score") or "0")
    sectors = news.get("related_sectors") or ""
    summary = news.get("summary") or ""
    reason = news.get("reason") or ""

    # 构建评论列表字符串
    comments_text = ""
    if comments:
        for i, c in enumerate(comments, 1):
            content = (c.get("content") or "").strip()
            if content:
                comments_text += f"{i}. {content}\n"
    else:
        comments_text = "（无评论）"

    return template \
        .replace("<<news_id>>", str(news_id)) \
        .replace("<<title>>", title) \
        .replace("<<score>>", score) \
        .replace("<<sectors>>", sectors) \
        .replace("<<summary>>", summary) \
        .replace("<<reason>>", reason) \
        .replace("<<comments>>", comments_text)


def parse_llm_result(text_blocks: list) -> dict | None:
    """从 content blocks 解析 JSON（忽略 thinking block）"""
    for blk in reversed(text_blocks):
        if blk.get("type") != "text":
            continue
        txt = blk.get("text", "").strip()
        txt = re.sub(r"^```json\s*", "", txt)
        txt = re.sub(r"\s*```\s*$", "", txt)
        try:
            return json.loads(txt)
        except json.JSONDecodeError:
            pass
        m = re.search(r"\{[\s\S]+}", txt)
        if m:
            try:
                return json.loads(m.group())
            except json.JSONDecodeError:
                pass
    return None


def call_llm(prompt: str) -> dict | None:
    """调用 LLM"""
    try:
        import asyncio
        from script.api_clients.llm_client import call_async_raw as _raw_fn

        async def _call():
            blocks = await _raw_fn(prompt, timeout=60)
            if blocks is None:
                return None
            return parse_llm_result(blocks)

        return asyncio.run(_call())
    except Exception as e:
        print(f"  [LLM ERR] {e}")
        return None


def ensure_table(conn):
    """建表（幂等）"""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS backtest_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            news_id INTEGER NOT NULL,
            valid_comments TEXT,
            optimization_suggestions TEXT,
            raw_llm_result TEXT,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        )
    """)
    conn.commit()


def backtest_news(news_id: int, conn) -> dict | None:
    """回测某条新闻的所有评论，工作流三步"""
    row = conn.execute(
        "SELECT id, title, summary, reason, related_sectors, importance_score "
        "FROM importance WHERE id = ?", (news_id,)
    ).fetchone()
    if not row:
        print(f"[SKIP] 新闻 {news_id} 不存在")
        return None

    news = {
        "id": row[0],
        "title": row[1] or "",
        "summary": row[2] or "",
        "reason": row[3] or "",
        "related_sectors": row[4] or "",
        "importance_score": row[5] or 0,
    }

    comment_rows = conn.execute(
        "SELECT id, content FROM comments WHERE news_id = ? ORDER BY created_at DESC",
        (news_id,),
    ).fetchall()

    comments = [{"id": r[0], "content": r[1] or ""} for r in comment_rows]

    print(f"\n新闻 {news_id}: {news['title'][:40]} | {len(comments)} 条评论")

    prompt = build_prompt(news, comments)
    result = call_llm(prompt)

    if result is None:
        print(f"  [SKIP] news={news_id} 解析失败")
        return None

    # 持久化
    valid_comments = json.dumps(result.get("有效评论") or [], ensure_ascii=False)
    suggestions = json.dumps(result.get("优化建议") or [], ensure_ascii=False)

    conn.execute("""
        INSERT INTO backtest_results
            (news_id, valid_comments, optimization_suggestions, raw_llm_result)
        VALUES (?, ?, ?, ?)
    """, (news_id, valid_comments, suggestions, json.dumps(result, ensure_ascii=False)))
    conn.commit()

    suggestions_list = result.get("优化建议") or []
    print(f"  有效评论: {len(result.get('有效评论') or [])} 条")
    print(f"  优化建议: {len(suggestions_list)} 条")
    for s in suggestions_list[:3]:
        print(f"    [{s.get('类别','')}] {str(s.get('建议',''))[:50]}")

    return result


def backtest_recent(days: int, conn) -> list:
    """回测最近N天的所有新闻+评论"""
    since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    print(f"[回测] 最近 {days} 天 | {since} 后")

    rows = conn.execute(
        "SELECT id FROM importance WHERE created_at >= ? ORDER BY created_at DESC", (since,)
    ).fetchall()

    results = []
    for (nid,) in rows:
        r = backtest_news(nid, conn)
        if r:
            results.append(r)
    return results


def main():
    parser = argparse.ArgumentParser(description="新闻评分回测工作流")
    parser.add_argument("--days", type=int, default=7, help="回测最近N天（默认7）")
    parser.add_argument("--news-id", type=int, help="只回测指定新闻ID")
    args = parser.parse_args()

    conn = get_conn()
    ensure_table(conn)

    if args.news_id is not None:
        backtest_news(args.news_id, conn)
    else:
        results = backtest_recent(args.days, conn)
        print(f"\n[汇总] 共回测 {len(results)} 条新闻")

    conn.close()


if __name__ == "__main__":
    main()