"""
log/__init__.py - 日志模块

统一日志输出到 logs/YYYY-MM-DD/<module>.log

使用：
    from script.log import log, log_error, init_log, api_exception_handler

    init_log()                          # 初始化全局日志
    app.add_exception_handler(Exception, api_exception_handler)  # FastAPI 异常处理
"""

from .log import log, log_error, timestamp_print, init_log, api_exception_handler, request_log_middleware

__all__ = ["log", "log_error", "timestamp_print", "init_log", "api_exception_handler", "request_log_middleware"]