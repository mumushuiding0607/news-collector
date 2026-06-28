"""
feedback_service.py - 反馈和评论业务服务

从 api/feedback.py 提取的业务逻辑。
"""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from script.db import auth_db
from script.db.feedback_db import (
    submit_feedback as _submit_feedback,
    get_comments_by_news as _get_comments,
    add_comment as _add_comment,
    get_comment_owner as _get_comment_owner,
    update_comment as _update_comment,
    delete_comment as _delete_comment,
)


def get_user_by_token(token: str):
    return auth_db.get_user_by_token(token)


def submit_feedback(token: str | None, feedback_type: str, content: str) -> dict:
    """提交反馈"""
    user_id = None
    if token:
        user = get_user_by_token(token)
        if user:
            user_id = user[0]
    _submit_feedback(user_id, feedback_type, content)
    return {"success": True, "message": "感谢反馈"}


def get_comments(news_id: int) -> dict:
    """获取新闻评论"""
    comments = _get_comments(news_id)
    return {"count": len(comments), "comments": comments}


def add_comment(token: str, news_id: int, content: str) -> dict:
    """添加评论"""
    user = get_user_by_token(token)
    if not user:
        raise ValueError("请先登录")
    _add_comment(news_id, user[0], content)
    return {"success": True, "message": "评论成功"}


def update_comment(token: str, comment_id: int, content: str) -> dict:
    """修改评论"""
    user = get_user_by_token(token)
    if not user:
        raise ValueError("请先登录")
    owner = _get_comment_owner(comment_id)
    if owner is None:
        raise ValueError("评论不存在")
    if owner != user[0]:
        raise ValueError("无权修改此评论")
    _update_comment(comment_id, content)
    return {"success": True, "message": "修改成功"}


def delete_comment(token: str, comment_id: int) -> dict:
    """删除评论"""
    user = get_user_by_token(token)
    if not user:
        raise ValueError("请先登录")
    owner = _get_comment_owner(comment_id)
    if owner is None:
        raise ValueError("评论不存在")
    if owner != user[0]:
        raise ValueError("无权删除此评论")
    _delete_comment(comment_id)
    return {"success": True, "message": "删除成功"}