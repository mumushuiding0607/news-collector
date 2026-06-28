"""
log.py - 统一日志模块

所有程序日志必须引用此模块：
    from script.log import log

特性：
  - 日志输出到 logs/YYYY-MM-DD/<module>.log，按日期分目录
  - 同一模块同一日期的日志追加写入
  - 控制台 + 文件双输出
  - 支持异常堆栈打印

FastAPI 集成（main.py）：
    from script.log import init_log
    init_log()
    app = FastAPI()
    app.add_exception_handler(Exception, api_exception_handler)
"""

import logging
import os
import sys
import traceback
from datetime import datetime, date
from pathlib import Path
from logging.handlers import RotatingFileHandler

from script.bootstrap import LOG_DIR


# ---------------------------------------------------------------------------
# 日志格式
# ---------------------------------------------------------------------------

LOG_FMT = "%(asctime)s  [%(levelname)s]  [%(name)s:%(lineno)d]  %(message)s"
DATE_FMT = "%Y-%m-%d %H:%M:%S"


# ---------------------------------------------------------------------------
# 控制台处理器（兼容 Windows 中文编码）
# ---------------------------------------------------------------------------

class ConsoleHandler(logging.StreamHandler):
    def emit(self, record):
        try:
            super().emit(record)
        except UnicodeEncodeError:
            msg = self.format(record)
            safe = msg.encode("gbk", errors="replace").decode("gbk")
            print(safe, flush=True)


# ---------------------------------------------------------------------------
# 全局日志配置
# ---------------------------------------------------------------------------

_log_initialized = False


def init_log():
    """
    初始化全局日志配置。

    - 所有模块的日志输出到 logs/YYYY-MM-DD/global.log
    - 包含完整堆栈信息
    - 自动创建日志目录
    """
    global _log_initialized
    if _log_initialized:
        return

    LOG_DIR.mkdir(parents=True, exist_ok=True)

    # 全局配置
    logging.basicConfig(
        level=logging.INFO,
        format=LOG_FMT,
        datefmt=DATE_FMT,
        handlers=[],
        force=True,
    )

    # 根日志器
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # 清空现有 handlers
    root_logger.handlers.clear()

    # 控制台 handler
    console = ConsoleHandler(stream=sys.stdout)
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter(LOG_FMT, datefmt=DATE_FMT))
    root_logger.addHandler(console)

    # 文件 handler（按日期）
    today = date.today()
    log_file = LOG_DIR / today.strftime("%Y-%m-%d") / "global.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter(LOG_FMT, datefmt=DATE_FMT))
    root_logger.addHandler(file_handler)

    _log_initialized = True


# ---------------------------------------------------------------------------
# 旧版兼容接口（每个模块写入专属日志文件）
# ---------------------------------------------------------------------------

_module_file_handlers: dict[str, logging.Handler] = {}
_error_file_handler: logging.Handler | None = None


def _get_module_handler(module: str) -> logging.Handler:
    """获取或创建模块专属的按日期滚动的文件 handler"""
    if module in _module_file_handlers:
        return _module_file_handlers[module]

    today_s = date.today().strftime("%Y-%m-%d")
    log_file = LOG_DIR / today_s / f"{module}.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)

    handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding="utf-8",
    )
    handler.setLevel(logging.INFO)
    handler.setFormatter(logging.Formatter(LOG_FMT, datefmt=DATE_FMT))
    _module_file_handlers[module] = handler
    return handler


def _get_error_handler() -> logging.Handler:
    """获取或创建 error.log 的 handler（按日期滚动）"""
    global _error_file_handler
    if _error_file_handler is not None:
        return _error_file_handler

    today_s = date.today().strftime("%Y-%m-%d")
    error_log_file = LOG_DIR / today_s / "error.log"
    error_log_file.parent.mkdir(parents=True, exist_ok=True)

    handler = RotatingFileHandler(
        error_log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding="utf-8",
    )
    handler.setLevel(logging.ERROR)
    handler.setFormatter(logging.Formatter(LOG_FMT, datefmt=DATE_FMT))
    _error_file_handler = handler
    return handler


def log(module: str, msg: str):
    """兼容旧代码的 log(module, msg) 接口"""
    logger = logging.getLogger(module)
    if not logger.handlers:
        logger.addHandler(_get_module_handler(module))
        logger.setLevel(logging.INFO)
        logger.propagate = False  # 不向根日志器传播，避免重复
    logger.info(msg)


def log_error(module: str, msg: str, exc_info=None):
    """错误日志：同时输出到模块日志和 error.log

    Args:
        module: 模块名
        msg: 错误消息
        exc_info: 异常信息，传 None 时自动获取当前异常堆栈
    """
    logger = logging.getLogger(module)
    if not logger.handlers:
        logger.addHandler(_get_module_handler(module))
        logger.setLevel(logging.INFO)
        logger.propagate = False

    # 记录到模块日志（含堆栈）
    if exc_info is None:
        exc_info = sys.exc_info()
    logger.error(msg, exc_info=exc_info)

    # 额外写入 error.log（含堆栈，堆栈中已有文件位置）
    if exc_info and exc_info[0]:
        error_lines = "".join(traceback.format_exception(*exc_info))
        full_msg = f"{msg}\n{error_lines}"
    else:
        full_msg = msg
    error_handler = _get_error_handler()
    # 直接写入，格式与 LOG_FMT 一致，时间戳由 handler 的 formatter 生成
    ts = datetime.now().strftime(DATE_FMT)
    error_handler.emit(
        logging.LogRecord(module, logging.ERROR, __file__, 0, full_msg, (), None)
    )


def timestamp_print(msg: str):
    """带时间戳的打印（兼容旧接口）"""
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


# ---------------------------------------------------------------------------
# FastAPI 异常处理
# ---------------------------------------------------------------------------

from fastapi import Request, status
from fastapi.responses import JSONResponse


async def api_exception_handler(request: Request, exc: Exception):
    """捕获所有未处理异常，记录完整堆栈后返回 500"""
    detail = (
        f"[API Exception] {request.method} {request.url.path}\n"
        f"  exception: {exc}\n"
        f"  traceback: {traceback.format_exc()}"
    )
    log_error("api", detail)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": str(exc), "type": type(exc).__name__},
    )


# ---------------------------------------------------------------------------
# 请求日志中间件
# ---------------------------------------------------------------------------

async def request_log_middleware(request: Request, call_next):
    """记录每个 API 请求的进入和响应，含耗时统计"""
    logger = logging.getLogger("api")
    path = request.url.path
    method = request.method

    # 写入专用耗时日志文件（logs/YYYY-MM-DD/timing.log）
    import time
    from pathlib import Path
    from datetime import date
    from script.bootstrap import LOG_DIR

    start_ms = time.perf_counter()

    logger.info(f"[Request] {method} {path}")

    try:
        response = await call_next(request)
        elapsed_ms = round((time.perf_counter() - start_ms) * 1000, 1)
        logger.info(f"[Response] {method} {path} -> {response.status_code}  ({elapsed_ms}ms)")

        # 写入耗时日志
        timing_log = LOG_DIR / date.today().strftime("%Y-%m-%d") / "timing.log"
        timing_log.parent.mkdir(parents=True, exist_ok=True)
        with timing_log.open("a", encoding="utf-8") as f:
            f.write(f"{datetime.now().strftime('%H:%M:%S')}  {method} {path}  {elapsed_ms}ms\n")

        return response
    except Exception as e:
        detail = (
            f"[Unhandled] {method} {path}\n"
            f"  exception: {e}\n"
            f"  traceback: {traceback.format_exc()}"
        )
        log_error("api", detail)
        raise