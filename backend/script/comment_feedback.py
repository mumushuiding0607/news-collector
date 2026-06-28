"""
comment_feedback.py - 用户评论反馈处理

工作流：
1. 查询未处理的评论
2. 批量过滤无效评论，对有效评论总结整合
3. 生成用户反馈内容并存储

使用方式：
    python -m script.comment_feedback [--limit N] [--dry-run]
"""

from __future__ import annotations

import argparse
import asyncio
import json

from script.bootstrap import *
from script.db import get_conn, put_conn
from llm import call_async_raw

# ---------------------------------------------------------------------------
# 路径与常量
# ---------------------------------------------------------------------------

PROMPT_FILE = PROMPT_DIR / "意见建议评论处理.md"

LLM_TIMEOUT = 120
# 3000 字符输入 → 1-2 个 feedback，约 1000 tokens；client.py 截断保护兜底翻倍
COMMENT_FEEDBACK_MAX_TOKENS = 2000
DEFAULT_MAX_CHARS = 3000  # 每批最大总字符数


# ---------------------------------------------------------------------------
# 数据库操作
# ---------------------------------------------------------------------------


def get_unprocessed_comments(limit: int = 50) -> list[dict]:
    """查询未处理的评论"""
    conn = get_conn()
    try:
        rows = conn.execute("""
            SELECT c.id, c.content, c.news_id
            FROM comments c
            WHERE c.processed = 0 OR c.processed IS NULL
            ORDER BY c.created_at DESC
            LIMIT ?
        """, (limit,)).fetchall()
        return [
            {"id": row[0], "content": row[1], "news_id": row[2]}
            for row in rows
        ]
    finally:
        put_conn(conn)


def mark_comments_processed(comment_ids: list[int]) -> int:
    """标记评论为已处理"""
    if not comment_ids:
        return 0
    conn = get_conn()
    try:
        placeholders = ",".join("?" * len(comment_ids))
        cursor = conn.execute(
            f"UPDATE comments SET processed = 1 WHERE id IN ({placeholders})",
            comment_ids,
        )
        conn.commit()
        return cursor.rowcount
    finally:
        put_conn(conn)


def save_feedback(news_id: int, feedback_content: str) -> int:
    """存储用户反馈"""
    conn = get_conn()
    try:
        cursor = conn.execute("""
            INSERT INTO comment_feedback (news_id, feedback_content)
            VALUES (?, ?)
        """, (news_id, feedback_content))
        conn.commit()
        return cursor.lastrowid
    finally:
        put_conn(conn)


def ensure_table() -> None:
    """确保表存在"""
    conn = get_conn()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_feedback_summary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                news_id INTEGER NOT NULL,
                feedback_content TEXT,
                created_at TEXT DEFAULT (datetime('now','localtime'))
            )
        """)
        conn.commit()
    finally:
        put_conn(conn)


# ---------------------------------------------------------------------------
# 批量处理
# ---------------------------------------------------------------------------


def split_by_total_chars(comments: list[dict], max_chars: int = DEFAULT_MAX_CHARS) -> list[list[dict]]:
    """按总字符数切分评论"""
    batches = []
    current_batch = []
    current_chars = 0

    for comment in comments:
        comment_chars = len(comment["content"])
        if current_chars + comment_chars > max_chars and current_batch:
            batches.append(current_batch)
            current_batch = []
            current_chars = 0
        current_batch.append(comment)
        current_chars += comment_chars

    if current_batch:
        batches.append(current_batch)
    return batches


# ---------------------------------------------------------------------------
# Prompt 构建
# ---------------------------------------------------------------------------


def _load_template() -> str:
    """加载提示词模板"""
    if PROMPT_FILE.exists():
        return PROMPT_FILE.read_text(encoding="utf-8")
    raise FileNotFoundError(f"Prompt file not found: {PROMPT_FILE}")


def build_prompt(comments: list[dict]) -> str:
    """构建提示词"""
    template = _load_template()
    comments_text = ""
    for i, c in enumerate(comments, 1):
        content = (c.get("content") or "").strip()
        if content:
            comments_text += f"{i}. {content}\n"
    return template.replace("<<comments>>", comments_text)


# ---------------------------------------------------------------------------
# LLM 调用
# ---------------------------------------------------------------------------


async def call_llm(comments: list[dict]) -> list[dict] | None:
    """调用 LLM 处理评论"""
    if not comments:
        return None
    prompt = build_prompt(comments)
    try:
        blocks = await call_async_raw(prompt, timeout=LLM_TIMEOUT)
        if not blocks:
            return None
        return _parse_response(blocks)
    except Exception as e:
        print(f"  [LLM ERR] {e}")
        return None


def _parse_response(text_blocks: list[str]) -> list[dict] | None:
    """解析 LLM 返回的 JSON 数组"""
    import re
    for blk in reversed(text_blocks):
        txt = blk.strip()
        txt = re.sub(r"^```json\s*", "", txt)
        txt = re.sub(r"\s*```\s*$", "", txt)
        try:
            result = json.loads(txt)
            if isinstance(result, list):
                return result
            return [result]
        except json.JSONDecodeError:
            pass
        m = re.search(r"\[[\s\S]*\]", txt)
        if m:
            try:
                result = json.loads(m.group())
                if isinstance(result, list):
                    return result
                return [result]
            except json.JSONDecodeError:
                pass
    return None


# ---------------------------------------------------------------------------
# 工作流
# ---------------------------------------------------------------------------


async def run_workflow(limit: int = 50, dry_run: bool = False) -> None:
    """执行工作流"""
    print(f"\n{'=' * 60}")
    print(f"[工作流] limit={limit}, dry_run={dry_run}")
    print(f"{'=' * 60}")

    # 1. 查询未处理评论
    comments = get_unprocessed_comments(limit=limit)
    if not comments:
        print("[完成] 没有未处理的评论")
        return

    print(f"[步骤1] 获取 {len(comments)} 条未处理评论")

    # 2. 按 news_id 分组
    news_groups: dict[int, list[dict]] = {}
    for c in comments:
        nid = c["news_id"]
        if nid not in news_groups:
            news_groups[nid] = []
        news_groups[nid].append(c)

    print(f"[步骤2] 按新闻分组，共 {len(news_groups)} 条新闻")

    # 3. 处理每条新闻的评论
    print("[步骤3] 处理评论...")
    ensure_table()
    saved_count = 0
    all_processed_ids: list[int] = []

    for news_id, news_comments in news_groups.items():
        all_feedback: list[str] = []

        # 按字符数切分批次
        batches = split_by_total_chars(news_comments, DEFAULT_MAX_CHARS)
        for batch in batches:
            result = await call_llm(batch)
            if result is None:
                print(f"  [WARN] news_id={news_id} 处理失败，跳过这批")
                continue

            # 提取反馈内容（数组格式）
            for item in result:
                feedback = item.get("feedback", "")
                if feedback:
                    all_feedback.append(feedback)

            # 收集已处理的评论ID
            for c in batch:
                all_processed_ids.append(c["id"])

        # 保存结果
        if all_feedback:
            feedback_content = "\n---\n".join(all_feedback)
            if not dry_run:
                save_feedback(news_id, feedback_content)
            saved_count += 1
            print(f"  news_id={news_id}: 反馈已保存")

    # 标记评论为已处理
    if all_processed_ids and not dry_run:
        mark_comments_processed(all_processed_ids)

    print(f"\n{'=' * 60}")
    print(f"[完成] 处理 {len(news_groups)} 条新闻，生成 {saved_count} 条反馈")
    print(f"{'=' * 60}")


# ---------------------------------------------------------------------------
# CLI 入口
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description="用户评论反馈处理")
    parser.add_argument("--limit", type=int, default=50, help="每次处理的评论条数（默认50）")
    parser.add_argument("--dry-run", action="store_true", help="仅模拟，不写入数据库")
    args = parser.parse_args()

    asyncio.run(run_workflow(limit=args.limit, dry_run=args.dry_run))


if __name__ == "__main__":
    main()