"""
Feedback & Comments API

只负责路由和参数校验，业务逻辑委托给 core.feedback_service。
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from core.feedback_service import (
    submit_feedback, get_comments as fb_get_comments,
    add_comment, update_comment as fb_update_comment,
    delete_comment as fb_delete_comment,
)

router = APIRouter(prefix="/feedback", tags=["反馈"])
comments_router = APIRouter(prefix="/comments", tags=["评论"])


class FeedbackRequest(BaseModel):
    content: str
    type: str = "suggestion"


class CommentRequest(BaseModel):
    news_id: int
    content: str


class UpdateCommentRequest(BaseModel):
    content: str


@router.post("")
def submit_feedback_api(req: FeedbackRequest, request: Request):
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    result = submit_feedback(token, req.type, req.content)
    return result


@comments_router.get("/{news_id}")
def get_comments_api(news_id: int):
    return fb_get_comments(news_id)


@comments_router.post("")
def add_comment_api(req: CommentRequest, request: Request):
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    try:
        return add_comment(token, req.news_id, req.content)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


@comments_router.put("/{comment_id}")
def update_comment_api(comment_id: int, req: UpdateCommentRequest, request: Request):
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    try:
        return fb_update_comment(token, comment_id, req.content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@comments_router.delete("/{comment_id}")
def delete_comment_api(comment_id: int, request: Request):
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    try:
        return fb_delete_comment(token, comment_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))