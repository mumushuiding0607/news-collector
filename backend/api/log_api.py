"""
Log API - 日志管理

只负责路由和参数校验，业务逻辑委托给 core.log_service。
需要管理员权限。
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from core.log_service import (
    list_log_dates, list_log_files,
    read_log_content, stream_log_tail,
)
from backend.api._auth import require_admin

router = APIRouter(prefix="/logs", tags=["日志"])


@router.get("/dates")
def get_log_dates(request: Request):
    """获取所有日志日期列表"""
    require_admin(request)
    return {"dates": list_log_dates()}


@router.get("/files")
def get_log_files(request: Request, date: str | None = None):
    """获取日志文件列表，可按日期筛选"""
    require_admin(request)
    return {"files": list_log_files(date)}


@router.get("/content")
def get_log_content(
    request: Request,
    path: str = Query(..., description="日志文件路径"),
    offset: int = Query(0, description="行偏移量"),
    limit: int = Query(500, description="最大返回行数"),
):
    """读取日志文件内容（分页）"""
    require_admin(request)
    try:
        return read_log_content(path, offset, limit)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/tail")
def get_log_tail(
    request: Request,
    path: str = Query(..., description="日志文件路径"),
    lines: int = Query(100, description="返回最后 N 行"),
):
    """流式读取日志文件最后 N 行（用于实时查看）"""
    require_admin(request)
    try:
        content = stream_log_tail(path, lines)
        return StreamingResponse(
            content=str(content),
            media_type="text/plain; charset=utf-8",
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"日志文件不存在: {path}")