"""
feedback_db.py - 反馈和评论的数据库 CRUD

封装 feedback 和 comments 表的数据库操作。
"""
from __future__ import annotations
from script.db import get_conn, put_conn


# ============ feedback ============
def submit_feedback(user_id: int | None, feedback_type: str, content: str) -> int:
    """提交反馈，返回 feedback id"""
    conn = get_conn()
    try:
        cursor = conn.execute(
            "INSERT INTO feedback (user_id, type, content) VALUES (?, ?, ?)",
            (user_id, feedback_type, content),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        put_conn(conn)


# ============ comments ============
def _mask_email(email: str | None) -> str:
    """邮箱脱敏：user@example.com → u***r@example.com"""
    if not email:
        return ""
    at = email.rfind("@")
    if at <= 1:
        return "***"
    return email[0] + "***" + email[at - 1:]


def _mask_phone(phone: str | None) -> str:
    """手机号脱敏：13812345678 → 138****5678"""
    if not phone or len(phone) < 7:
        return phone or ""
    return phone[:3] + "****" + phone[-4:]


def get_comments_by_news(news_id: int, limit: int = 50) -> list:
    """获取新闻的评论列表"""
    conn = get_conn()
    try:
        rows = conn.execute("""
            SELECT c.id, c.content, c.created_at, u.email, u.phone, u.nickname
            FROM comments c
            LEFT JOIN auth_users u ON c.user_id = u.id
            WHERE c.news_id = ?
            ORDER BY c.created_at DESC
            LIMIT ?
        """, (news_id, limit)).fetchall()
        comments = []
        for row in rows:
            email, phone, nickname = row[3], row[4], row[5]
            if email:
                display = _mask_email(email)
            elif phone:
                display = _mask_phone(phone)
            else:
                display = nickname or "匿名用户"
            comments.append({
                "id": row[0],
                "content": row[1],
                "created_at": row[2],
                "display_name": display,
                "nickname": nickname or "匿名用户",
            })
        return comments
    finally:
        put_conn(conn)


def add_comment(news_id: int, user_id: int, content: str) -> int:
    """添加评论，返回 comment id"""
    conn = get_conn()
    try:
        cursor = conn.execute(
            "INSERT INTO comments (news_id, user_id, content) VALUES (?, ?, ?)",
            (news_id, user_id, content),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        put_conn(conn)


def get_comment_owner(comment_id: int) -> int | None:
    """获取评论的 owner user_id，无则返回 None"""
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT user_id FROM comments WHERE id = ?", (comment_id,)
        ).fetchone()
        return row[0] if row else None
    finally:
        put_conn(conn)


def update_comment(comment_id: int, content: str) -> bool:
    """修改评论，返回是否成功"""
    conn = get_conn()
    try:
        conn.execute(
            "UPDATE comments SET content = ? WHERE id = ?",
            (content, comment_id),
        )
        conn.commit()
        return True
    finally:
        put_conn(conn)


def delete_comment(comment_id: int) -> bool:
    """删除评论，返回是否成功"""
    conn = get_conn()
    try:
        conn.execute("DELETE FROM comments WHERE id = ?", (comment_id,))
        conn.commit()
        return True
    finally:
        put_conn(conn)