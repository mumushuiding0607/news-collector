"""
Feedback & Comments API
"""
import sys
import hashlib
import random
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "script"))

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from common.db.connection import get_conn

router = APIRouter(prefix="/feedback", tags=["反馈"])


class FeedbackRequest(BaseModel):
    content: str
    type: str = "suggestion"


class CommentRequest(BaseModel):
    news_id: int
    content: str


class UpdateCommentRequest(BaseModel):
    content: str


def get_user_from_token(token: str, conn):
    row = conn.execute(
        "SELECT u.id, u.phone FROM auth_tokens t JOIN auth_users u ON t.user_id = u.id WHERE t.token = ?",
        (token,)
    ).fetchone()
    return row


def _generate_token() -> str:
    raw = f"{random.random()}{datetime.now().isoformat()}"
    return hashlib.sha256(raw.encode()).hexdigest()


@router.post("")
def submit_feedback(req: FeedbackRequest, request: Request):
    """提交意见反馈"""
    conn = get_conn()
    try:
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        user = get_user_from_token(token, conn)
        user_id = user[0] if user else None

        conn.execute(
            "INSERT INTO feedback (user_id, type, content) VALUES (?, ?, ?)",
            (user_id, req.type, req.content)
        )
        conn.commit()
        return {"success": True, "message": "感谢反馈"}
    finally:
        conn.close()


# ============ 评论路由（挂载到 /api/comments） ============
comments_router = APIRouter(prefix="/comments", tags=["评论"])


@comments_router.get("/{news_id}")
def get_comments(news_id: int):
    conn = get_conn()
    try:
        rows = conn.execute("""
            SELECT c.id, c.content, c.created_at, u.phone, u.nickname
            FROM comments c
            LEFT JOIN auth_users u ON c.user_id = u.id
            WHERE c.news_id = ?
            ORDER BY c.created_at DESC LIMIT 50
        """, (news_id,)).fetchall()

        comments = []
        for row in rows:
            comments.append({
                "id": row[0],
                "content": row[1],
                "created_at": row[2],
                "user_phone": ("游客" + row[3][-4:]) if row[3] else "匿名",
                "nickname": row[4] or "匿名用户",
            })
        return {"count": len(comments), "comments": comments}
    finally:
        conn.close()


@comments_router.post("")
def add_comment(req: CommentRequest, request: Request):
    conn = get_conn()
    try:
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        user = get_user_from_token(token, conn)
        if not user:
            raise HTTPException(status_code=401, detail="请先登录")

        conn.execute(
            "INSERT INTO comments (news_id, user_id, content) VALUES (?, ?, ?)",
            (req.news_id, user[0], req.content)
        )
        conn.commit()
        return {"success": True, "message": "评论成功"}
    finally:
        conn.close()


@comments_router.put("/{comment_id}")
def update_comment(comment_id: int, req: UpdateCommentRequest, request: Request):
    """修改评论（仅本人可修改）"""
    conn = get_conn()
    try:
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        user = get_user_from_token(token, conn)
        if not user:
            raise HTTPException(status_code=401, detail="请先登录")

        # 验证评论归属
        row = conn.execute(
            "SELECT user_id FROM comments WHERE id = ?", (comment_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="评论不存在")
        if row[0] != user[0]:
            raise HTTPException(status_code=403, detail="无权修改此评论")

        conn.execute(
            "UPDATE comments SET content = ? WHERE id = ?",
            (req.content, comment_id)
        )
        conn.commit()
        return {"success": True, "message": "修改成功"}
    finally:
        conn.close()


@comments_router.delete("/{comment_id}")
def delete_comment(comment_id: int, request: Request):
    """删除评论（仅本人可删除）"""
    conn = get_conn()
    try:
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        user = get_user_from_token(token, conn)
        if not user:
            raise HTTPException(status_code=401, detail="请先登录")

        row = conn.execute(
            "SELECT user_id FROM comments WHERE id = ?", (comment_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="评论不存在")
        if row[0] != user[0]:
            raise HTTPException(status_code=403, detail="无权删除此评论")

        conn.execute("DELETE FROM comments WHERE id = ?", (comment_id,))
        conn.commit()
        return {"success": True, "message": "删除成功"}
    finally:
        conn.close()