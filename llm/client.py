"""
client.py - LLM 调用客户端

封装与 MiniMax API 的交互，支持同步/异步调用，
自动处理 thinking block 干扰和响应解析。
"""

import json
import logging
import re
import sys
from pathlib import Path

import aiohttp
import requests

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 路径设置：确保能 import 到 script/common/（有 db/ 和 config.py）
# ---------------------------------------------------------------------------

_ROOT = Path(__file__).resolve().parent.parent
_SCRIPT = str(_ROOT / "script")

for p in [_SCRIPT, str(_ROOT)]:
    if p in sys.path:
        sys.path.remove(p)
sys.path.insert(0, _SCRIPT)
sys.path.insert(0, str(_ROOT))

from common.config import LLM_API_KEY as _MINIMAX_API_KEY
from common.config import LLM_BASE_URL as _MINIMAX_BASE_URL
from common.config import LLM_MODEL as _MINIMAX_MODEL

if not _MINIMAX_API_KEY:
    raise RuntimeError(
        "未配置 MINIMAX_API_KEY 环境变量。"
        "请在 .env 文件中设置 MINIMAX_API_KEY=sk-cp-xxxxxx"
    )


# ---------------------------------------------------------------------------
# 响应解析
# ---------------------------------------------------------------------------

_JSON_RE = re.compile(r'^```json\s*', re.MULTILINE)
_BACKTICK_RE = re.compile(r'^```\s*$', re.MULTILINE)
_THINKING_PREVIEW = 500  # thinking block 截断字符数


def parse_response(text_blocks: list[str]) -> dict | None:
    """
    从 LLM 返回的多个 text block 中解析 JSON。

    策略：从后向前尝试解析，失败后检查"不会引起市场波动"文本。
    """
    for i in range(len(text_blocks) - 1, -1, -1):
        tb = text_blocks[i].strip()
        if not tb:
            continue
        tb = _JSON_RE.sub('', tb)
        tb = _BACKTICK_RE.sub('', tb)
        m = re.search(r'[\[{][\s\S]*[\]}]', tb)
        if m:
            try:
                result = json.loads(m.group())
                if isinstance(result, list) and len(result) == 1:
                    result = result[0]
                return result
            except json.JSONDecodeError:
                pass

    combined = "\n".join(text_blocks).strip()
    if not re.search(r'"will_flunctuate"\s*:\s*(true|false)', combined):
        if "不会引起市场波动" in combined:
            return {"will_flunctuate": False}
    return None


# ---------------------------------------------------------------------------
# 请求构建
# ---------------------------------------------------------------------------

def _headers() -> dict:
    return {
        "X-Api-Key": _MINIMAX_API_KEY,
        "Content-Type": "application/json",
        "anthropic-version": "2023-06-01"
    }


def _payload(prompt: str, max_tokens: int) -> dict:
    return {
        "model": _MINIMAX_MODEL,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}]
    }


def _text_blocks(content_blocks: list[dict]) -> list[str]:
    out = []
    for b in content_blocks:
        t = b.get("type", "")
        if t == "text":
            out.append(b.get("text", ""))
        elif t == "thinking":
            out.append(b.get("thinking", "")[:_THINKING_PREVIEW])
    return out


# ---------------------------------------------------------------------------
# 同步调用
# ---------------------------------------------------------------------------

def call(
    prompt: str,
    *,
    timeout: int = 60,
    max_tokens: int = 2000,
    retry: int = 2
) -> dict | None:
    url = f"{_MINIMAX_BASE_URL}/v1/messages"
    last_err = None
    for attempt in range(retry + 1):
        try:
            r = requests.post(url, headers=_headers(), json=_payload(prompt, max_tokens), timeout=timeout)
            if r.status_code != 200:
                logger.warning("[HTTP %d] %s", r.status_code, r.text[:200])
                last_err = f"HTTP {r.status_code}"
                continue
            blocks = _text_blocks(r.json().get("content", []))
            return parse_response(blocks)
        except requests.Timeout:
            logger.warning("[API] 超时 %ds", timeout)
            last_err = "timeout"
        except requests.ConnectionError as e:
            logger.warning("[API] 连接错误: %s", e)
            last_err = str(e)
        except json.JSONDecodeError as e:
            logger.warning("[API] JSON错误: %s", e)
            last_err = f"JSON: {e}"
        except Exception as e:
            logger.error("[API] %s: %s", type(e).__name__, e)
            last_err = str(e)
        if attempt < retry:
            time.sleep(2 ** attempt)
    logger.error("[API] 重试耗尽: %s", last_err)
    return None


# ---------------------------------------------------------------------------
# 异步调用
# ---------------------------------------------------------------------------

async def call_async_raw(
    prompt: str,
    *,
    timeout: int = 60,
    max_tokens: int = 16000
) -> list[str] | None:
    url = f"{_MINIMAX_BASE_URL}/v1/messages"
    try:
        async with aiohttp.ClientSession() as sess:
            async with sess.post(
                url, headers=_headers(), json=_payload(prompt, max_tokens),
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as r:
                if r.status != 200:
                    text = await r.text()
                    logger.warning("[HTTP %d] %s", r.status, text[:200])
                    return None
                blocks = _text_blocks((await r.json()).get("content", []))
                return blocks
    except aiohttp.ServerTimeoutError:
        logger.warning("[API] 异步超时 %ds", timeout)
    except aiohttp.ClientError as e:
        logger.warning("[API] 异步连接错误: %s", e)
    except Exception as e:
        logger.error("[API] %s: %s", type(e).__name__, e)
    return None


async def call_async(
    prompt: str,
    *,
    timeout: int = 60,
    max_tokens: int = 600
) -> dict | None:
    blocks = await call_async_raw(prompt, timeout=timeout, max_tokens=max_tokens)
    return parse_response(blocks) if blocks else None
