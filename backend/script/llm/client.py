"""
client.py - LLM 调用客户端

封装与 MiniMax API 的交互，支持同步/异步调用，
自动处理 thinking block 干扰和响应解析。

遵循 BEST_PRACTICE.md：
  - 自定义异常类 LLMCallError
  - 完整文档字符串
  - 关键参数用关键字参数
  - 使用 Pydantic LLMConfig 配置类
"""

from __future__ import annotations

import json
import re
import time
import asyncio
from typing import Any

import aiohttp
import requests

from script.config import get_llm_config
from script.log import log as _module_log

# LLM 客户端的日志统一写到 logs/YYYY-MM-DD/llm_client.log，
# 避免 Python 默认 logger 走 root handler（无法按日期分割、无法按模块筛选）。
def _log(msg: str, *args: Any) -> None:
    if args:
        msg = msg % args
    _module_log("llm_client", msg)

# ---------------------------------------------------------------------------
# 调用节流（仅最小间隔，不再有全局冷却）
# ---------------------------------------------------------------------------
#
# 历史设计曾有"连续失败 N 次 → 全局冷却 N 秒"的机制，但会导致一个批次失败
# 拖垮所有调用方（同步接口也受影响）。当前 call_async_raw 已自带退避重试，
# 全局冷却收益小、副作用大，移除。

_API_MIN_INTERVAL = 1.0  # 两次 LLM 调用之间的最小间隔（秒）
_API_LAST_CALL_TIME: float = 0.0  # 上次调用时间


async def _wait_if_needed() -> None:
    """等待满足最小调用间隔。"""
    global _API_LAST_CALL_TIME
    import time
    elapsed = time.time() - _API_LAST_CALL_TIME
    if elapsed < _API_MIN_INTERVAL:
        await asyncio.sleep(_API_MIN_INTERVAL - elapsed)


def _update_call_time() -> None:
    """更新最后调用时间。"""
    global _API_LAST_CALL_TIME
    import time
    _API_LAST_CALL_TIME = time.time()


# ---------------------------------------------------------------------------
# 异常定义
# ---------------------------------------------------------------------------


class LLMCallError(Exception):
    """LLM 调用失败时抛出的异常。"""

    def __init__(self, message: str, cause: Exception | None = None) -> None:
        super().__init__(message)
        self.__cause__ = cause


# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------

_CONFIG = get_llm_config()

# ---------------------------------------------------------------------------
# 响应解析
# ---------------------------------------------------------------------------

_JSON_RE = re.compile(r"^```json\s*", re.MULTILINE)
_BACKTICK_RE = re.compile(r"^```\s*$", re.MULTILINE)
_THINKING_PREVIEW = 500  # thinking block 截断字符数

def _looks_truncated(blocks: list[str] | None) -> bool:
    """判断 LLM 返回是否疑似被截断。

    尝试从 blocks 中提取完整 JSON（支持 markdown 代码块包裹的 JSON）。
    能提取并解析出有效 JSON 则不算截断。
    """
    if not blocks:
        return False
    # 合并所有 text block
    full_text = "\n".join(blocks)
    # 去掉 markdown 代码块（常见格式）
    import re, json
    text_clean = re.sub(r"^```json\s*", "", full_text, flags=re.MULTILINE)
    text_clean = re.sub(r"^```\s*$", "", text_clean, flags=re.MULTILINE).strip()
    # 尝试提取 JSON 数组或对象
    for pattern in [r'\[[\s\S]*\]', r'\{[\s\S]*\}']:
        m = re.search(pattern, text_clean)
        if m:
            try:
                json.loads(m.group())
                return False  # 能解析完整 JSON，不算截断
            except json.JSONDecodeError:
                pass
    return True


def _fix_unescaped_quotes_in_json(text: str) -> str:
    """修复 LLM 输出中字符串值内未转义的双引号。

    LLM 经常将中文标题中的双引号（如 "磷酸铁锂时刻"）直接复制到 JSON 字符串值中，
    导致 JSON 解析失败。本函数通过状态机识别字符串边界，将字符串值内的
    未转义双引号转义为 \\\"。

    通用算法：扫描字符时跟踪"是否在字符串内"状态。当遇到未转义的双引号时：
    - 若不在字符串内：标记为字符串开始
    - 若在字符串内：检查后续字符判断是字符串结束（后跟 ,/}/]/:/空白）
      还是内容中的引号（应转义）

    Args:
        text: 包含 JSON 的文本

    Returns:
        修复后的文本
    """
    result = []
    in_string = False
    i = 0
    n = len(text)
    # JSON 结构分隔符集合：字符串结束符后通常跟这些
    structural_chars = set(",}]: \t\n\r")

    while i < n:
        ch = text[i]

        if ch == "\\" and i + 1 < n:
            # 转义字符，原样保留两个字符
            result.append(ch)
            result.append(text[i + 1])
            i += 2
            continue

        if ch == '"':
            if not in_string:
                # 字符串开始
                in_string = True
                result.append(ch)
                i += 1
                continue
            else:
                # 已经在字符串内，判断这是结束引号还是内容引号
                # 结束引号的特征：后面紧跟 ,/}/]/:/空白或字符串结尾
                j = i + 1
                while j < n and text[j] in " \t\n\r":
                    j += 1
                if j >= n or text[j] in ",}]:":
                    # 字符串结束
                    in_string = False
                    result.append(ch)
                    i += 1
                    continue
                else:
                    # 内容中的引号，需要转义
                    result.append('\\"')
                    i += 1
                    continue

        result.append(ch)
        i += 1

    return "".join(result)


def parse_response(text_blocks: list[str]) -> dict | None:
    """从 LLM 返回的多个 text block 中解析 JSON。

    策略：
    1. 从后向前尝试严格解析
    2. 失败时尝试修复 LLM 输出中常见的未转义双引号问题
    3. 修复后再次解析
    4. 最后检查"不会引起市场波动"文本

    Args:
        text_blocks: LLM 返回的 content 块列表

    Returns:
        解析后的字典，解析失败返回 None
    """
    for i in range(len(text_blocks) - 1, -1, -1):
        tb = text_blocks[i].strip()
        if not tb:
            continue
        tb = _JSON_RE.sub("", tb)
        tb = _BACKTICK_RE.sub("", tb)
        m = re.search(r"[\[{][\s\S]*[\]}]", tb)
        if not m:
            continue
        json_str = m.group()
        # 先尝试严格解析
        try:
            result = json.loads(json_str)
            if isinstance(result, list) and len(result) == 1:
                result = result[0]
            return result
        except json.JSONDecodeError:
            # 严格解析失败，尝试修复未转义的双引号
            try:
                fixed = _fix_unescaped_quotes_in_json(json_str)
                result = json.loads(fixed)
                if isinstance(result, list) and len(result) == 1:
                    result = result[0]
                return result
            except (json.JSONDecodeError, Exception):
                pass

    combined = "\n".join(text_blocks).strip()
    if not re.search(r'"will_flunctuate"\s*:\s*(true|false)', combined):
        if "不会引起市场波动" in combined:
            return {"will_flunctuate": False}
    return None


# ---------------------------------------------------------------------------
# 请求构建
# ---------------------------------------------------------------------------


def _headers() -> dict[str, str]:
    """构建 HTTP 请求头。"""
    return {
        "X-Api-Key": _CONFIG.api_key,
        "Content-Type": "application/json",
        "anthropic-version": "2023-06-01",
    }


def _payload(prompt: str, max_tokens: int | None, thinking_budget_tokens: int | None = None) -> dict[str, Any]:
    """构建请求体。

    Args:
        prompt: 用户提示词
        max_tokens: 输出总上限（thinking + text）。None=不限制（不传给 API）
        thinking_budget_tokens: thinking 单独上限（None=禁用 thinking；>0=启用并设预算）
    """
    if thinking_budget_tokens is not None:
        thinking_cfg = {"type": "enabled", "budget_tokens": thinking_budget_tokens}
    else:
        thinking_cfg = {"type": "disabled"}
    payload: dict[str, Any] = {
        "model": _CONFIG.model,
        "messages": [{"role": "user", "content": prompt}],
        "thinking": thinking_cfg,
    }
    # None=不限制：不传给 API，让模型自然输出
    if max_tokens is not None:
        payload["max_tokens"] = max_tokens
    return payload


def _text_blocks(content_blocks: list[dict[str, Any]]) -> list[str]:
    """从 content 块列表提取纯文本。

    只接受 `type="text"` 的 block。`type="thinking"` 的 block 即使模型未真正产出
    答案也可能存在（如 miniMax-M2.7 即便 thinking disabled 也会返回），但 thinking
    是内部推理，提取它的"最后一行"会被 `_looks_truncated` 误判为截断，触发无谓的
    Stage 2 翻倍——一律丢弃。

    没有 text block → 返回空列表 → 上游判 `kind='empty'` → Stage 1 退避重试。
    """
    out = []
    for b in content_blocks:
        t = b.get("type", "")
        if t == "text":
            text = b.get("text", "")
            if text:
                out.append(text)
    return out


# ---------------------------------------------------------------------------
# 同步调用
# ---------------------------------------------------------------------------


def call(
    prompt: str,
    *,
    timeout: int | None = None,
    max_tokens: int | None = None,
    retry: int | None = None,
) -> dict | None:
    """同步调用 LLM 接口。

    Args:
        prompt: 发送给 LLM 的提示词
        timeout: 请求超时秒数（默认从配置读取）
        max_tokens: 最大返回 token 数（默认从配置读取）
        retry: 最大重试次数（默认从配置读取）

    Returns:
        LLM 返回的解析结果字典，失败返回 None
    """
    if timeout is None:
        timeout = _CONFIG.timeout
    if retry is None:
        retry = _CONFIG.max_retries

    url = f"{_CONFIG.base_url}/v1/messages"
    last_err: Exception | str | None = None

    for attempt in range(retry + 1):
        try:
            r = requests.post(
                url,
                headers=_headers(),
                json=_payload(prompt, max_tokens),
                timeout=timeout,
            )
            if r.status_code != 200:
                _log("[HTTP %d] %s", r.status_code, r.text[:200])
                last_err = f"HTTP {r.status_code}"
                continue
            blocks = _text_blocks(r.json().get("content", []))
            return parse_response(blocks)
        except requests.Timeout:
            _log("[API] 超时 %ds", timeout)
            last_err = "timeout"
        except requests.ConnectionError as e:
            _log("[API] 连接错误: %s", e)
            last_err = e
        except json.JSONDecodeError as e:
            _log("[API] JSON 解析错误: %s", e)
            last_err = e
        except Exception as e:
            _log("[API] %s: %s", type(e).__name__, e)
            last_err = e

        if attempt < retry:
            time.sleep(2**attempt)

    _log("[API] 重试耗尽: %s", last_err)
    return None


# ---------------------------------------------------------------------------
# 异步调用
# ---------------------------------------------------------------------------


async def _do_call_async_raw_classified(
    prompt: str,
    *,
    timeout: int,
    max_tokens: int | None,
    thinking_budget_tokens: int | None = None,
) -> tuple[list[str] | None, str | None]:
    """单次异步 HTTP 调用，返回 (blocks, error_kind)。

    error_kind:
      - None: 调用成功，blocks 有效（可能含截断内容，由 _looks_truncated 判定）
      - 'timeout': 请求超时（aiohttp.ServerTimeoutError / asyncio.TimeoutError）
      - 'connection': 连接错误（aiohttp.ClientError 等）
      - 'http_error': HTTP 非 200
      - 'empty': HTTP 200 但 content 为空（API 返回成功无 text block）
      - 'decode': 响应 JSON 解析失败

    区分这些类型让 call_async_raw 能针对性选择"退避重试"还是"翻倍 max_tokens"。
    """
    url = f"{_CONFIG.base_url}/v1/messages"
    try:
        async with aiohttp.ClientSession() as sess:
            async with sess.post(
                url,
                headers=_headers(),
                json=_payload(prompt, max_tokens, thinking_budget_tokens),
                timeout=aiohttp.ClientTimeout(total=timeout),
            ) as r:
                if r.status != 200:
                    text = await r.text()
                    _log("[HTTP %d] %s", r.status, text[:200])
                    return None, 'http_error'
                try:
                    data = await r.json()
                except Exception as e:
                    _log("[API] JSON 解析错误: %s", e)
                    return None, 'decode'
                blocks = _text_blocks(data.get("content", []))
                if not blocks:
                    # HTTP 200 但没有 text block。记录关键诊断信息：
                    # - content 数量、block 类型分布（区分"完全没有 content" vs "全是 thinking 没 text"）
                    # - stop_reason / model / usage
                    # 这样下次出现 None 时能区分是 API bug 还是模型本身没生成。
                    content = data.get("content", [])
                    block_types = [b.get("type") for b in content] if isinstance(content, list) else []
                    _log(
                        "[API] empty 响应：HTTP 200 但无 text block | content 数量=%d, block 类型=%s, stop_reason=%s, model=%s, usage=%s",
                        len(content) if isinstance(content, list) else -1,
                        block_types or "[]",
                        data.get("stop_reason"),
                        data.get("model"),
                        data.get("usage"),
                    )
                    return None, 'empty'
                return blocks, None
    except asyncio.TimeoutError:
        _log("[API] 异步超时 %ds", timeout)
        return None, 'timeout'
    except aiohttp.ServerTimeoutError:
        _log("[API] 异步超时 %ds", timeout)
        return None, 'timeout'
    except aiohttp.ClientError as e:
        _log("[API] 异步连接错误: %s", e)
        return None, 'connection'
    except Exception as e:
        _log("[API] %s: %s", type(e).__name__, e)
        return None, 'unknown'
    return None, 'unknown'


async def call_async_raw(
    prompt: str,
    *,
    timeout: int | None = None,
    max_tokens: int | None = None,
    status_holder: dict | None = None,
    thinking_budget_tokens: int | None = None,
) -> list[str] | None:
    """异步调用 LLM 接口，返回原始 text block 列表。

    单一重试策略：Stage 1 最多 2 次退避重试（total 3 次尝试）。
    **已删除 Stage 2 翻倍**：max_tokens 限制 + 翻倍 = API 慢时 60min 兜底，纯浪费。
    现在 max_tokens=None → 不传给 API → LLM 自然输出 → 不会截断 → 不需要翻倍。

    Args:
        prompt: 发送给 LLM 的提示词
        timeout: 请求超时秒数（默认从配置读取）
        max_tokens: 最大返回 token 数（None=不限制，不传给 API；保留参数仅为向后兼容）
        status_holder: 可选 dict，调用结束后会写入：
            - last_kind: str | None  最终一次调用的 kind（成功时为 'ok'）
            - attempts: list[dict]   每次调用的 {kind, elapsed, max_tokens} 列表
            - final_outcome: str     'ok' / 'stage1_exhausted'
        thinking_budget_tokens: thinking 单独上限（None=禁用 thinking；>0=启用并设预算）
            用于控制 thinking 不耗光 token 配额。Anthropic 兼容字段，minimaxi 应支持。

    Returns:
        LLM 返回的 text block 列表，失败返回 None（Stage 1 用尽）。
    """
    if timeout is None:
        timeout = _CONFIG.timeout
    # max_tokens=None → 不限制（不传给 API）。早期 scorer 就是这个行为，效率高。
    # 不限制 = LLM 不会截断 = 不需要翻倍重试 = 不会 60min 兜底。

    if status_holder is not None:
        status_holder.clear()
        status_holder["attempts"] = []

    await _wait_if_needed()

    # Stage 1：API 瞬时故障 → 退避重试（不退避 max_tokens）
    # 重试 2 次（total 3 次尝试）：超时场景下 2 次重试足够，再多只是浪费 token
    MAX_API_RETRIES = 2
    last_kind: str | None = None
    blocks: list[str] | None = None
    for attempt in range(1, MAX_API_RETRIES + 1):
        _update_call_time()
        t0 = time.time()
        blocks, kind = await _do_call_async_raw_classified(
            prompt, timeout=timeout, max_tokens=max_tokens,
            thinking_budget_tokens=thinking_budget_tokens,
        )
        elapsed = time.time() - t0
        last_kind = kind
        if status_holder is not None:
            status_holder["attempts"].append({
                "kind": kind if kind is not None else "ok",
                "elapsed": round(elapsed, 1),
                "max_tokens": max_tokens,
            })
        # 成功：blocks 有效且非截断
        is_truncated = _looks_truncated(blocks) if blocks else False
        if kind is None and blocks is not None and not is_truncated:
            if status_holder is not None:
                status_holder["last_kind"] = "ok"
                status_holder["final_outcome"] = "ok"
            return blocks
        # 诊断：truncated 但有 blocks
        if is_truncated and blocks:
            full_text = "\n".join(blocks)
            _log("[API] _looks_truncated=True | text 前300: %s", full_text[:300])
            if status_holder is not None:
                status_holder["last_kind"] = "ok"
                status_holder["final_outcome"] = "ok"
            return blocks
        if attempt < MAX_API_RETRIES:
            kind_desc = kind or 'truncated'
            _log("[API] 调用失败（%s, max_tokens=%s, 耗时 %.1fs），第 %d/%d 次重试",
                 kind_desc, str(max_tokens), elapsed, attempt + 1, MAX_API_RETRIES)
            # 指数退避：5s / 10s（API 慢时短退避反复打回无意义，给服务器恢复时间）
            await asyncio.sleep(5.0 * (2 ** (attempt - 1)))

    # Stage 1 全部失败后 → 直接放弃，不做翻倍重试
    # 历史设计曾有 Stage 2（截断翻倍 max_tokens 4000→8000→16000→32000），
    # 但实测发现：API 慢时翻倍只会**重复浪费**——每一级都先吃 3×300s=900s 才升级，
    # worst case 4 级 = 60min/批。同时每次重试都是 token 浪费（无产出）。
    # 删掉 Stage 2：失败就返回，让上层标记 batch_failed 留给下次重试。
    if last_kind is not None:
        _log("[API] 放弃重试：%s（max_tokens=%s）", last_kind, str(max_tokens))
    if status_holder is not None:
        status_holder["last_kind"] = last_kind or "unknown"
        status_holder["final_outcome"] = "stage1_exhausted"
    return blocks


async def call_async(
    prompt: str,
    *,
    timeout: int | None = None,
    max_tokens: int | None = None,
    thinking_budget_tokens: int | None = None,
) -> dict | None:
    """异步调用 LLM 接口，返回解析后的字典。

    Args:
        prompt: 发送给 LLM 的提示词
        timeout: 请求超时秒数（默认从配置读取）
        max_tokens: 最大返回 token 数（默认从配置读取）
        thinking_budget_tokens: thinking 单独上限（透传给 call_async_raw）

    Returns:
        LLM 返回的解析结果字典，失败返回 None
    """
    if timeout is None:
        timeout = _CONFIG.timeout
    if max_tokens is None:
        max_tokens = 600

    blocks = await call_async_raw(
        prompt, timeout=timeout, max_tokens=max_tokens,
        thinking_budget_tokens=thinking_budget_tokens,
    )
    return parse_response(blocks) if blocks else None