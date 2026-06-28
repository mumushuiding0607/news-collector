"""
config/__init__.py - 配置管理模块（统一导出）

提供：
  - APP_ROOT, DB_PATH, LOG_DIR 等路径常量
  - LLM 配置（LLMConfig, get_llm_config, LLM_API_KEY 等）
  - load_env() 环境变量加载

使用：
    from script.config import load_env, get_llm_config, APP_ROOT
    load_env()  # 在其他模块 import 前调用
"""

from __future__ import annotations

import os
from pathlib import Path

# 加载 .env（如果存在）
from script.config.env import load_env as _load_env, load_env

_load_env()

# bootstrap 负责 sys.path 和 APP_ROOT 设置，config 只依赖其结果
from script.bootstrap import APP_ROOT, DB_PATH, LOG_DIR, CACHE_DIR
from script.bootstrap import CONFIG_DIR, PROMPT_DIR, SOURCES_CONFIG

# ==================== Pydantic 配置类 ====================

from pydantic import BaseModel


class LLMConfig(BaseModel):
    """LLM 配置项，支持环境变量覆盖。"""

    api_key: str = ""
    base_url: str = "https://api.minimaxi.com/anthropic"
    model: str = "MiniMax-M2.7"
    timeout: int = 60
    max_tokens: int = 2000
    max_retries: int = 2

    @classmethod
    def from_env(cls) -> "LLMConfig":
        """从环境变量构建配置。"""
        return cls(
            api_key=os.environ.get("MINIMAX_API_KEY", ""),
            base_url=os.environ.get("MINIMAX_BASE_URL", "https://api.minimaxi.com/anthropic"),
            model=os.environ.get("MINIMAX_MODEL", "MiniMax-M2.7"),
            timeout=int(os.environ.get("LLM_TIMEOUT", 60)),
            max_tokens=int(os.environ.get("LLM_MAX_TOKENS", 2000)),
            max_retries=int(os.environ.get("LLM_MAX_RETRIES", 2)),
        )


# 全局配置实例（惰性加载）
_llm_config: LLMConfig | None = None


def get_llm_config() -> LLMConfig:
    """获取 LLM 配置单例。"""
    global _llm_config
    if _llm_config is None:
        _llm_config = LLMConfig.from_env()
    return _llm_config


# ==================== 导出（向后兼容） ====================

LLM_API_KEY = os.environ.get("MINIMAX_API_KEY", "")
LLM_BASE_URL = os.environ.get("MINIMAX_BASE_URL", "https://api.minimaxi.com/anthropic")
LLM_MODEL = os.environ.get("MINIMAX_MODEL", "MiniMax-M2.7")

__all__ = [
    # 路径常量
    "APP_ROOT",
    "DB_PATH",
    "LOG_DIR",
    "CACHE_DIR",
    "CONFIG_DIR",
    "PROMPT_DIR",
    "SOURCES_CONFIG",
    # LLM 配置
    "LLM_API_KEY",
    "LLM_BASE_URL",
    "LLM_MODEL",
    "LLMConfig",
    "get_llm_config",
    # .env 加载
    "load_env",
]