# learning_log.py - 学习过程 HTML 日志工具
#
# 保存学习过程中的 HTML，用于调试和验证。
#
# 使用方式：
#   from script.discovery.util.learning_log import get_learning_log_dir, save_learning_html

from pathlib import Path
from datetime import date
from urllib.parse import urlparse

from script.bootstrap import LOG_DIR


def get_learning_log_dir() -> Path:
    """获取学习日志目录 logs/<date>/learning/"""
    today_str = date.today().strftime("%Y-%m-%d")
    log_dir = LOG_DIR / today_str / "learning"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def save_learning_html(url: str, html: str, step: str, log_fn=None):
    """
    保存学习过程中的 HTML 到日志目录。

    Args:
        url: 数据源 URL（用于生成文件名）
        html: HTML 内容
        step: 当前步骤（如 "list_raw", "list_cleaned", "article_raw", "article_cleaned"）
        log_fn: 日志函数（默认 print）
    """
    if log_fn is None:
        def log_fn(msg):
            print(msg)
    try:
        parsed = urlparse(url)
        host = parsed.netloc.replace(".", "_").replace(":", "_")
        path = parsed.path.strip("/").replace("/", "_")[:50]
        filename = f"{step}_{host}_{path}.html" if path else f"{step}_{host}.html"
        filepath = get_learning_log_dir() / filename
        filepath.write_text(html[:500_000], encoding="utf-8")  # 最多保存500KB
        log_fn(f"[日志] 保存 HTML 到 {filepath.name}")
    except Exception as e:
        log_fn(f"[日志] 保存 HTML 失败: {e}")