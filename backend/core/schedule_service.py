"""
schedule_service.py - 定时任务管理业务服务

处理定时任务的 CRUD 和触发操作：
- tasks.json 配置文件读写
- 任务列表查询
- 新增/修改/删除任务
- 手动触发任务
"""

from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path
from typing import Optional

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_TASKS_CONFIG = _PROJECT_ROOT / "backend" / "config" / "tasks.json"

logger = logging.getLogger(__name__)


def _ensure_dir():
    """确保 scheduler 目录存在"""
    _TASKS_CONFIG.parent.mkdir(parents=True, exist_ok=True)


def _load_config() -> dict:
    """加载任务配置"""
    _ensure_dir()
    if not _TASKS_CONFIG.exists():
        return {"enabled": True, "tasks": []}
    import json
    return json.loads(_TASKS_CONFIG.read_text(encoding="utf-8"))


def _save_config(data: dict) -> None:
    """保存任务配置"""
    _ensure_dir()
    from script.common.jsonutil import write_json
    write_json(data, _TASKS_CONFIG)


# ============ 查询 ============
def get_tasks() -> dict:
    """获取所有定时任务"""
    return _load_config()


def get_task(task_id: str) -> dict | None:
    """获取指定任务"""
    config = _load_config()
    for task in config.get("tasks", []):
        if task.get("id") == task_id:
            return task
    return None


# ============ CRUD ============
def create_task(task_data: dict) -> dict:
    """新增任务"""
    config = _load_config()

    task_id = task_data.get("id", "")
    if not task_id:
        raise ValueError("任务 ID 不能为空")

    # 检查 ID 冲突
    for t in config.get("tasks", []):
        if t.get("id") == task_id:
            raise ValueError(f"任务 ID {task_id} 已存在")

    # 验证 handler
    handler = task_data.get("handler", "")
    if not handler:
        raise ValueError("handler 不能为空")

    task = {
        "id": task_id,
        "name": task_data.get("name", task_id),
        "description": task_data.get("description", ""),
        "cron": task_data.get("cron", ""),
        "enabled": bool(task_data.get("enabled", True)),
        "handler": handler,
    }

    config.setdefault("tasks", []).append(task)
    _save_config(config)
    return task


def update_task(task_id: str, updates: dict) -> dict:
    """修改任务"""
    config = _load_config()

    target = None
    for t in config.get("tasks", []):
        if t.get("id") == task_id:
            target = t
            break

    if not target:
        raise ValueError(f"任务 {task_id} 不存在")

    # 允许更新的字段
    for key in ("name", "description", "cron", "enabled", "handler"):
        if key in updates:
            target[key] = updates[key]

    _save_config(config)
    return target


def delete_task(task_id: str) -> bool:
    """删除任务"""
    config = _load_config()

    tasks = config.get("tasks", [])
    new_tasks = [t for t in tasks if t.get("id") != task_id]

    if len(new_tasks) == len(tasks):
        raise ValueError(f"任务 {task_id} 不存在")

    config["tasks"] = new_tasks
    _save_config(config)
    return True


# ============ 触发 ============

# 任务级别互斥锁：防止同一任务并发执行（手动触发时也须互斥）
_running_tasks: dict[str, bool] = {}
_task_lock = __import__("threading").Lock()


def _run_task_in_background(task_id: str, handler: str):
    """后台线程中执行任务"""
    # 检查任务是否已在运行，防止并发执行同一任务
    with _task_lock:
        if _running_tasks.get(task_id):
            logger.info(f"[Schedule] 任务 {task_id} 已在运行中，跳过本次触发")
            return
        _running_tasks[task_id] = True

    try:
        if handler == "script.crawl.crawler.main":
            import asyncio
            from script.crawl.crawler import main as crawler_main
            asyncio.run(crawler_main())
            logger.info(f"[Schedule] 任务 {task_id} 执行完成")

        elif handler == "backend.service.news_pipeline.run_pipeline":
            from backend.service.news_pipeline import run_pipeline
            run_pipeline()
            logger.info(f"[Schedule] 任务 {task_id} 执行完成")

        else:
            logger.error(f"[Schedule] 不支持的 handler: {handler}")

    except Exception as e:
        logger.exception(f"[Schedule] 任务 {task_id} 执行失败")
    finally:
        # 确保任务完成或失败后清除运行标记
        with _task_lock:
            _running_tasks.pop(task_id, None)


def trigger_task(task_id: str) -> dict:
    """手动触发任务（异步，后台执行）"""
    task = get_task(task_id)
    if not task:
        raise ValueError(f"任务 {task_id} 不存在")

    handler = task.get("handler", "")

    # 检查任务是否已在运行
    with _task_lock:
        if _running_tasks.get(task_id):
            return {"ok": False, "message": f"任务 {task_id} 已在运行中，拒绝重复触发"}

    logger.info(f"[Schedule] 手动触发任务（后台）: {task_id} -> {handler}")

    import threading
    threading.Thread(target=_run_task_in_background, args=(task_id, handler), daemon=True).start()

    return {"ok": True, "message": f"任务已触发：{task_id}"}