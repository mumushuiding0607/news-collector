"""
Schedule API - 定时任务管理

只负责路由和参数校验，业务逻辑委托给 core.schedule_service。
需要管理员权限。
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from core.schedule_service import (
    get_tasks, get_task,
    create_task, update_task, delete_task,
    trigger_task,
)
from backend.api._auth import require_admin

router = APIRouter(prefix="/schedule", tags=["定时任务"])


class CreateTaskRequest(BaseModel):
    id: str
    name: str
    description: str = ""
    cron: str = ""
    enabled: bool = True
    handler: str


class UpdateTaskRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    cron: str | None = None
    enabled: bool | None = None
    handler: str | None = None


@router.get("/tasks")
def list_tasks(request: Request):
    """获取所有定时任务"""
    require_admin(request)
    return get_tasks()


@router.get("/tasks/{task_id}")
def get_task_detail(request: Request, task_id: str):
    """获取指定任务"""
    require_admin(request)
    task = get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")
    return task


@router.post("/tasks")
def create_task_api(request: Request, body: CreateTaskRequest):
    """新增定时任务"""
    require_admin(request)
    try:
        return create_task(body.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/tasks/{task_id}")
def update_task_api(request: Request, task_id: str, body: UpdateTaskRequest):
    """修改定时任务"""
    require_admin(request)
    try:
        return update_task(task_id, body.model_dump(exclude_unset=True))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/tasks/{task_id}")
def delete_task_api(request: Request, task_id: str):
    """删除定时任务"""
    require_admin(request)
    try:
        delete_task(task_id)
        return {"ok": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/tasks/{task_id}/trigger")
def trigger_task_api(request: Request, task_id: str):
    """手动触发任务"""
    require_admin(request)
    try:
        return trigger_task(task_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))