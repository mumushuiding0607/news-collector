"""
env.py - 专用 .env 加载模块

功能：
  - 提供 load_env() 加载函数
  - 检查必需配置是否已填写，缺失则报错

使用：
    from config.env import load_env
    load_env()  # 在其他模块 import 前调用
"""

from __future__ import annotations

import os
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
_UNIFIED_ENV = _BACKEND_DIR / ".env"


def load_env() -> None:
    """
    加载 .env 配置到环境变量。

    流程：
      1. 将 backend/.env 加载到环境变量
      2. 检查必需配置是否已填写，缺失则抛出 MissingEnvError
    """
    if _UNIFIED_ENV.exists():
        from dotenv import load_dotenv
        load_dotenv(_UNIFIED_ENV, override=False)

    missing = []
    for key, val in os.environ.items():
        if key.startswith("REQ_") and not val:
            missing.append(key)

    if missing:
        raise RuntimeError(f"缺少必需配置: {', '.join(missing)}")


def get_env_path() -> Path:
    """返回统一的 .env 文件路径。"""
    return _UNIFIED_ENV