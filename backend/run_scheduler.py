"""
run_scheduler.py - 独立定时任务调度器

读取 admin/scheduler/tasks.json 中的任务配置，
按 cron 表达式自动调度执行，日志写入 logs/YYYY-MM-DD/scheduler.log。
"""

from __future__ import annotations

import json
import logging
import signal
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

# backend 目录加入 path，以便引用 script.log / script.bootstrap
_BACKEND_DIR = Path(__file__).resolve().parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from script.log import init_log
from script.bootstrap import LOG_DIR, APP_ROOT

init_log()

# 配置 scheduler 专属 logger，写入 logs/YYYY-MM-DD/scheduler.log
from logging.handlers import BaseRotatingHandler
from datetime import date


class _DatedFileHandler(BaseRotatingHandler):
    """每天日志写入 logs/YYYY-MM-DD/scheduler.log，自动切换日期目录"""

    def __init__(self, log_dir: Path, backupCount: int = 30):
        self._log_dir = log_dir
        self._backupCount = backupCount
        self._current_date = date.today()
        self._current_path = log_dir / self._current_date.strftime("%Y-%m-%d") / "scheduler.log"
        self._current_path.parent.mkdir(parents=True, exist_ok=True)
        super().__init__(filename=str(self._current_path), mode="a", encoding="utf-8", delay=False)

    def shouldRollover(self, record):
        return False  # 由 emit() 按日期判断是否切换

    def emit(self, record):
        try:
            today = date.today()
            if today != self._current_date:
                self._current_date = today
                self._current_path = self._log_dir / today.strftime("%Y-%m-%d") / "scheduler.log"
                self._current_path.parent.mkdir(parents=True, exist_ok=True)
                self.baseFilename = str(self._current_path)
                if self.stream:
                    self.stream.close()
                    self.stream = open(self.baseFilename, self.mode, encoding=self.encoding)
            super().emit(record)
        except Exception:
            self.handleError(record)


_handler = _DatedFileHandler(LOG_DIR)
_handler.setFormatter(logging.Formatter(
    "%(asctime)s  [%(levelname)s]  %(message)s",
    datefmt="%H:%M:%S",
))
logger = logging.getLogger("scheduler")
logger.setLevel(logging.INFO)
logger.addHandler(_handler)

# 项目根目录
PROJECT_ROOT = APP_ROOT
TASKS_CONFIG = PROJECT_ROOT / "backend" / "config" / "tasks.json"


# ============ 任务配置读写 ============

def _load_tasks() -> list[dict]:
    """加载 tasks.json，只返回 enabled=True 的任务"""
    if not TASKS_CONFIG.exists():
        return []
    data = json.loads(TASKS_CONFIG.read_text(encoding="utf-8"))
    if not data.get("enabled", True):
        return []
    return [t for t in data.get("tasks", []) if t.get("enabled", True)]


# ============ 任务执行（非阻塞线程池） ============

# 全局线程池，用于非阻塞执行耗时任务
_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="scheduler_task_")

# 任务级别互斥锁：防止同一任务并发执行（尤其是 news_pipeline 这种长时间任务）
_running_tasks: dict[str, bool] = {}
_task_lock = threading.Lock()


def _run_task_sync(task_id: str, handler: str, news_type: str = "股市新闻") -> None:
    """同步执行单个任务，捕获异常不抛出让调度器继续运行"""
    # 检查任务是否已在运行，防止并发执行同一任务
    with _task_lock:
        if _running_tasks.get(task_id):
            logger.info(f"[TASK_SKIP] task_id={task_id}  任务已在运行中，跳过本次触发")
            return
        _running_tasks[task_id] = True

    logger.info(f"[TASK_START] task_id={task_id}  handler={handler}")
    start = time.time()
    try:
        cmd = _build_subprocess_cmd(handler, news_type)
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
        )
        elapsed = time.time() - start
        output = (result.stdout + result.stderr).strip()
        # 过滤掉 crawl4ai 初始化日志
        output_lines = [l for l in output.splitlines() if "Crawl4AI" not in l]
        filtered_output = "\n".join(output_lines).strip()
        if result.returncode == 0:
            logger.info(f"[TASK_DONE] task_id={task_id}  elapsed={elapsed:.1f}s  returncode=0")
            # 解析 step6 输出获取缓存更新结果
            cache_info = {}
            for line in filtered_output.splitlines():
                if "Step 6 完成" in line:
                    try:
                        parts = line.split("Step 6 完成: ")[1]
                        cache_info["update"] = parts.strip()
                    except Exception:
                        pass
            if cache_info:
                logger.info(f"[CACHE_UPDATE] task_id={task_id}  {cache_info['update']}")
            else:
                logger.info(f"[CACHE_UPDATE] task_id={task_id}  (通过 run_pipeline 流程自动更新)")
            if filtered_output:
                logger.info(f"[TASK_OUTPUT] task_id={task_id}:\n{filtered_output[:500]}")
        else:
            logger.error(f"[TASK_ERROR] task_id={task_id}  elapsed={elapsed:.1f}s  returncode={result.returncode}")
            if filtered_output:
                logger.error(f"[TASK_OUTPUT] task_id={task_id}:\n{filtered_output[:500]}")
    except Exception as e:
        elapsed = time.time() - start
        logger.exception(f"[TASK_ERROR] task_id={task_id}  elapsed={elapsed:.1f}s  error={e}")
    finally:
        # 确保任务完成或失败后清除运行标记
        with _task_lock:
            _running_tasks.pop(task_id, None)


def _build_subprocess_cmd(handler: str, news_type: str = "股市新闻") -> list[str]:
    """构建 subprocess.run 命令列表，匹配 schedule_service.trigger_task"""
    from script.bootstrap import APP_ROOT as _LOCAL_APP_ROOT
    _LOCAL_ROOT = str(_LOCAL_APP_ROOT).replace('\\', '/')
    _type_env = f"NEWS_TYPE={news_type}"
    _prefix = (
        f"import os; os.environ['APP_ROOT'] = '{_LOCAL_ROOT}'; os.environ['NEWS_TYPE'] = '{news_type}'; "
        f"os.chdir('{_LOCAL_ROOT}'); "
        "import sys; sys.path.insert(0, 'backend'); "
    )
    _handlers = {
        "backend.service.news_pipeline.run_pipeline": _prefix + "from backend.service.news_pipeline import run_pipeline; run_pipeline()",
        "script.crawl.crawler.main": _prefix + "import asyncio; from script.crawl.crawler import main; asyncio.run(main())",
        "backend.core.news_service.update_sector_change_rates": _prefix + "from backend.core.news_service import NewsService; NewsService.update_sector_change_rates()",
        "script.discovery.source_discovery.discover_and_schedule": _prefix + "from script.discovery.source_discovery import discover_and_schedule; discover_and_schedule()",
        "script.anomaly_news.summary.generate": _prefix + "from script.anomaly_news.summary import generate; generate()",
        "backend.service.news_stocks.sync_news_stocks_change_rates": _prefix + "from backend.service.news_stocks import sync_news_stocks_change_rates; sync_news_stocks_change_rates()",
        "backend.service.ai_news_pipeline.run_pipeline": _prefix + "from backend.service.ai_news_pipeline import run_pipeline; run_pipeline()",
        "script.log.log_cleanup.cleanup_old_logs": _prefix + "from script.log.log_cleanup import cleanup_old_logs; cleanup_old_logs()",
    }
    if handler not in _handlers:
        raise ValueError(f"不支持的 handler: {handler}")
    return [sys.executable, "-c", _handlers[handler]]


def _run_task(task_id: str, handler: str, news_type: str = "股市新闻") -> None:
    """将任务提交到线程池异步执行，不阻塞调度器"""
    _executor.submit(_run_task_sync, task_id, handler, news_type)


# ============ cron 转换 ============

def _expand_step_field(field: str, max_val: int, base_default: int = 0) -> str:
    """
    将单个 cron 字段的步长格式展开为枚举列表。
    例如 '0/5' + max_val=60 -> '0,5,10,...55'
          '8/3' + max_val=24 -> '8,11,14,17,20,23'
          '*/20' + max_val=60 -> '0,20,40'
    """
    if '/' not in field:
        return field
    base, step = field.split('/')
    step = int(step)
    if base == '*':
        base_val = base_default
    else:
        base_val = int(base) if base != '0' else base_default
    vals = []
    current = base_val
    while current < max_val:
        vals.append(str(current))
        current += step
    return ','.join(vals)


def _convert_cron_step(cron_str: str) -> str:
    """
    将 Quartz 6 字段 cron 表达式（含 / 步长）转换为 APScheduler 支持的 5 字段格式。
    Quartz 格式: second minute hour day month weekday year
    例如 '0 0 8/3 * * MON-FRI':
      second=0, minute=0, hour=8/3, day='*', month='*', weekday='MON-FRI'
    等价 5 字段: '0 8,11,14,17 * * MON-FRI'
    """
    parts = cron_str.strip().split()
    if len(parts) == 6:
        second, minute, hour, day, month, weekday = parts
    else:
        return cron_str

    # 解析秒步长，如 '*/5' -> 忽略（由 IntervalTrigger 处理）
    minute = _expand_step_field(minute, 60, base_default=0)
    hour = _expand_step_field(hour, 24, base_default=0)
    day = _expand_step_field(day, 32, base_default=1)

    return f"{minute} {hour} {day} {month} {weekday}"


# ============ APScheduler 调度 ============

def _schedule_all_tasks(scheduler, tasks: list[dict]) -> None:
    """清除所有已有 job，按 tasks 重新注册"""
    scheduler.remove_all_jobs()
    for task in tasks:
        task_id = task["id"]
        cron = task.get("cron", "")
        handler = task.get("handler", "")
        if not cron or not handler:
            logger.warning(f"[SCHEDULER] 任务 {task_id} 缺少 cron 或 handler，跳过")
            continue
        try:
            from apscheduler.triggers.cron import CronTrigger
            from apscheduler.triggers.interval import IntervalTrigger

            parts = cron.strip().split()
            # 检测秒步长，如 "*/5 * * * * *" -> 使用 IntervalTrigger
            if len(parts) == 6 and parts[0].startswith("*/"):
                step = int(parts[0].split("/")[1])
                trigger = IntervalTrigger(seconds=step)
                logger.info(f"[SCHEDULER] 注册任务: {task_id}  interval={step}s (秒级任务)")
            elif len(parts) == 6:
                # 6字段标准 cron（无秒步长），转换为 5 字段
                converted = _convert_cron_step(cron)
                trigger = CronTrigger.from_crontab(converted)
                logger.info(f"[SCHEDULER] 注册任务: {task_id}  cron={converted}")
            else:
                # 5字段 cron，展开步长表达式（如 */20 -> 0,20,40）
                expanded = _expand_step_field(parts[0], 60, 0) + " " + \
                           _expand_step_field(parts[1], 24, 0) + " " + \
                           _expand_step_field(parts[2], 32, 1) + " " + \
                           parts[3] + " " + parts[4]
                trigger = CronTrigger.from_crontab(expanded)
                logger.info(f"[SCHEDULER] 注册任务: {task_id}  cron={expanded}")

            scheduler.add_job(
                _run_task,
                trigger,
                args=[task_id, handler, task.get("type", "股市新闻")],
                id=task_id,
                replace_existing=True,
            )
        except Exception as e:
            logger.error(f"[SCHEDULER] 注册任务失败 {task_id}: {e}")


# ============ 热加载监控 ============

class _TasksFileWatcher:
    """后台线程：轮询 tasks.json 文件变化，热加载任务"""

    def __init__(self, scheduler, interval: float = 5.0):
        self._scheduler = scheduler
        self._interval = interval
        self._stop_event = threading.Event()
        self._last_mtime = 0.0
        if TASKS_CONFIG.exists():
            self._last_mtime = TASKS_CONFIG.stat().st_mtime

    def start(self) -> None:
        t = threading.Thread(target=self._run, daemon=True)
        t.start()
        logger.info(f"[WATCHER] 启动文件监控，间隔 {self._interval}s，监控文件: {TASKS_CONFIG}")

    def stop(self) -> None:
        self._stop_event.set()

    def _run(self) -> None:
        while not self._stop_event.wait(self._interval):
            if not TASKS_CONFIG.exists():
                continue
            mtime = TASKS_CONFIG.stat().st_mtime
            if mtime != self._last_mtime:
                self._last_mtime = mtime
                logger.info("[WATCHER] 检测到 tasks.json 变化，重新加载任务")
                tasks = _load_tasks()
                _schedule_all_tasks(self._scheduler, tasks)


# ============ 信号处理 ============

class _SignalHandler:
    """统一处理 SIGINT / SIGTERM，实现优雅退出"""

    def __init__(self, scheduler, watcher: _TasksFileWatcher):
        self._scheduler = scheduler
        self._watcher = watcher
        self._shutdown_event = threading.Event()

    def request_shutdown(self, signum, frame) -> None:
        logger.info(f"[SIGNAL] 收到信号 {signum}，开始优雅退出...")
        self._watcher.stop()
        self._scheduler.shutdown(wait=True)
        logger.info("[SIGNAL] 调度器已停止")
        self._shutdown_event.set()

    @property
    def shutdown_event(self) -> threading.Event:
        return self._shutdown_event


# ============ 入口 ============

def _load_scheduler_config() -> dict:
    """加载 config.json 中的 scheduler 配置"""
    cfg_path = PROJECT_ROOT / "backend" / "config.json"
    if not cfg_path.exists():
        return {}
    return json.loads(cfg_path.read_text(encoding="utf-8")).get("scheduler", {})


def main() -> None:
    logger.info("=" * 50)
    logger.info("[SCHEDULER] 定时任务调度器启动")
    logger.info(f"[SCHEDULER] 读取配置: {TASKS_CONFIG}")

    from apscheduler.schedulers.blocking import BlockingScheduler
    scheduler = BlockingScheduler()
    watcher = _TasksFileWatcher(scheduler)

    sig_handler = _SignalHandler(scheduler, watcher)
    signal.signal(signal.SIGINT, sig_handler.request_shutdown)
    signal.signal(signal.SIGTERM, sig_handler.request_shutdown)

    tasks = _load_tasks()
    logger.info(f"[SCHEDULER] 加载到 {len(tasks)} 个任务")
    _schedule_all_tasks(scheduler, tasks)

    # 部署触发：trigOnDeploy 为 true 时立即执行一次
    deploy_triggered = [t["id"] for t in tasks if t.get("trigOnDeploy")]
    if deploy_triggered:
        logger.info(f"[SCHEDULER] 部署触发，任务数量: {len(deploy_triggered)}，任务列表: {', '.join(deploy_triggered)}")
        for task in tasks:
            if task.get("trigOnDeploy"):
                _run_task(task["id"], task.get("handler", ""))
    else:
        logger.info("[SCHEDULER] 部署触发，无任务被执行")

    watcher.start()

    logger.info("[SCHEDULER] 调度器运行中，等待任务触发...")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        pass

    sig_handler.shutdown_event.wait()
    logger.info("[SCHEDULER] 调度器已退出")


if __name__ == "__main__":
    main()
