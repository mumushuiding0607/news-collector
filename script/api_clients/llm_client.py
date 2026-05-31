"""
llm_client.py - LLM 调用封装模块

从 .env 加载 API 凭证，统一调用 Minimax API，
处理 thinking block 干扰 JSON 解析的问题。

.env 文件放在项目根目录（不上传 Git），示例：
    MINIMAX_API_KEY=sk-cp-xxxxxx
    MINIMAX_BASE_URL=https://api.minimaxi.com/anthropic
    MINIMAX_MODEL=MiniMax-M2.7
"""

import json
import os
import re
import requests
import aiohttp
from pathlib import Path
from dotenv import load_dotenv


# ---------------------------------------------------------------------------
# 环境加载
# ---------------------------------------------------------------------------

# .env 文件路径（放在项目根目录，不上传 Git）
_ENV_PATH = Path(__file__).resolve().parent.parent.parent / ".env"


def load_env():
    """从 .env 文件加载环境变量（仅加载一次）"""
    if _ENV_PATH.exists():
        load_dotenv(_ENV_PATH)


load_env()


# ---------------------------------------------------------------------------
# API 凭证
# ---------------------------------------------------------------------------

_MINIMAX_API_KEY = os.environ.get("MINIMAX_API_KEY", "")
_MINIMAX_BASE_URL = os.environ.get("MINIMAX_BASE_URL", "https://api.minimaxi.com/anthropic")
_MINIMAX_MODEL = os.environ.get("MINIMAX_MODEL", "MiniMax-M2.7")

if not _MINIMAX_API_KEY:
    raise RuntimeError(
        "未配置 Minimax API 密钥。\n"
        "请在 .env 文件中设置 MINIMAX_API_KEY=sk-cp-xxxxxx\n"
        "（.env 文件在项目根目录，不上传 Git）"
    )


# ---------------------------------------------------------------------------
# 核心接口
# ---------------------------------------------------------------------------

def parse_response(text_blocks: list[str]) -> dict | None:
    """
    从 LLM 返回的多个 text block 中解析 JSON 结果。

    处理逻辑：
    - 依次从后向前遍历各 block，尝试匹配并解析 JSON
    - 去掉 ```json ``` 等代码块标记
    - 全部 block 解析失败时，检查纯文本"不会引起市场波动"

    Returns:
        解析成功: dict（包含 will_flunctuate 等字段）
        解析失败且不是"不会波动"文本: None
        明确是不波动文本: {"will_flunctuate": False}
    """
    for i in range(len(text_blocks) - 1, -1, -1):
        tb = text_blocks[i].strip()
        if not tb:
            continue
        # 去掉 code block 标记（```json ... ``` 或 ``` ... ```）
        tb = re.sub(r'^```json\s*', '', tb, flags=re.MULTILINE)
        tb = re.sub(r'^```\s*$', '', tb, flags=re.MULTILINE)
        # 尝试找 JSON 对象或数组
        m = re.search(r'[\[{][\s\S]*[\]}]', tb)
        if m:
            try:
                result = json.loads(m.group())
                # 如果是数组且只包含一个元素，取第一个
                if isinstance(result, list) and len(result) == 1:
                    result = result[0]
                return result
            except json.JSONDecodeError:
                pass

    # 所有 block 都解析失败：检查是否是"不会引起市场波动"纯文本
    combined = "\n".join(text_blocks).strip()
    json_in_combined = bool(re.search(r'"will_flunctuate"\s*:\s*(true|false)', combined))
    if not json_in_combined and "不会引起市场波动" in combined:
        return {"will_flunctuate": False}

    return None


def call(prompt: str, timeout: int = 60, max_tokens: int = 2000, retry: int = 2) -> dict | None:
    """
    调用 Minimax LLM API。

    Args:
        prompt: 发送给 LLM 的提示词
        timeout: 请求超时秒数（默认60）
        max_tokens: 生成的最大token数（默认2000）
        retry: 失败重试次数（默认2）

    Returns:
        解析成功: dict（包含结构化字段）
        失败: None（API 错误 / 解析失败 / 网络异常）
    """
    headers = {
        "X-Api-Key": _MINIMAX_API_KEY,
        "Content-Type": "application/json",
        "anthropic-version": "2023-06-01"
    }

    payload = {
        "model": _MINIMAX_MODEL,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}]
    }

    url = f"{_MINIMAX_BASE_URL}/v1/messages"

    last_error = None
    for attempt in range(retry + 1):
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
            if resp.status_code != 200:
                print(f"  [HTTP {resp.status_code}] {resp.text[:200]}")
                last_error = f"HTTP {resp.status_code}"
                continue

            data = resp.json()
            content_blocks = data.get("content", [])

            # 分离 thinking 和 text：thinking 截断至 500 字符避免干扰
            text_blocks = []
            for block in content_blocks:
                btype = block.get("type", "")
                if btype == "text":
                    text_blocks.append(block.get("text", ""))
                elif btype == "thinking":
                    text_blocks.append(block.get("thinking", "")[:500])

            return parse_response(text_blocks)

        except requests.Timeout:
            print(f"  [API ERR] 请求超时 timeout={timeout}s")
            last_error = "timeout"
        except requests.ConnectionError as e:
            print(f"  [API ERR] 连接错误: {e}")
            last_error = f"connection error: {e}"
        except json.JSONDecodeError as e:
            print(f"  [API ERR] JSON解析失败: {e}")
            last_error = f"JSON error: {e}"
        except Exception as e:
            print(f"  [API ERR] 未知错误: {e}")
            last_error = f"error: {e}"

        if attempt < retry:
            import time
            time.sleep(2 ** attempt)  # 指数退避: 1s, 2s, 4s...

    print(f"  [API ERR] 全部重试失败，最后错误: {last_error}")
    return None


async def call_async_raw(prompt: str, timeout: int = 60) -> list[str] | None:
    """
    异步调用 Minimax LLM API，返回原始 text blocks（不解析）。

    Args:
        prompt: 发送给 LLM 的提示词
        timeout: 请求超时秒数

    Returns:
        成功: list[str]，各 text block 内容
        失败: None
    """
    headers = {
        "X-Api-Key": _MINIMAX_API_KEY,
        "Content-Type": "application/json",
        "anthropic-version": "2023-06-01"
    }

    payload = {
        "model": _MINIMAX_MODEL,
        "max_tokens": 16000,
        "messages": [{"role": "user", "content": prompt}]
    }

    url = f"{_MINIMAX_BASE_URL}/v1/messages"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    print(f"  [HTTP {resp.status}] {text[:200]}")
                    return None

                data = await resp.json()
                content_blocks = data.get("content", [])

                text_blocks = []
                for block in content_blocks:
                    btype = block.get("type", "")
                    if btype == "text":
                        text_blocks.append(block.get("text", ""))
                    elif btype == "thinking":
                        text_blocks.append(block.get("thinking", "")[:500])

                return text_blocks

    except aiohttp.ServerTimeoutError:
        print(f"  [API ERR] 异步请求超时 timeout={timeout}s")
        return None
    except aiohttp.ClientError as e:
        print(f"  [API ERR] 异步连接错误: {e}")
        return None
    except Exception as e:
        print(f"  [API ERR] {type(e).__name__}: {e}")
        return None


# ---------------------------------------------------------------------------
# 异步接口
# ---------------------------------------------------------------------------

async def call_async(prompt: str, timeout: int = 60, max_tokens: int = 600) -> dict | None:
    """
    异步调用 Minimax LLM API。

    Args:
        prompt: 发送给 LLM 的提示词
        timeout: 请求超时秒数
        max_tokens: 生成的最大token数（默认600，call_async_raw用16000）

    Returns:
        解析成功: dict（包含结构化字段）
        失败: None（API 错误 / 解析失败 / 网络异常）
    """
    text_blocks = await call_async_raw(prompt, timeout=timeout, max_tokens=max_tokens)
    if text_blocks is None:
        return None
    return parse_response(text_blocks)