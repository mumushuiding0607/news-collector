"""
boilerplate.py - Boilerplate 清理（文本级别）
"""

from __future__ import annotations

import re

from ._constants import (
    BOILERPLATE_PATTERNS,
    _LINE_SEP_RE,
    _LINE_FOREIGN_RE,
    _LINE_LINK_RE,
    _LINK_STRIP_RE,
    _LINE_CN_RE,
    _LINE_FOREIGN_COUNT_RE,
    _LINE_PUNCT_RE,
    _BP_DATE_RE,
)


def is_boilerplate_line(line: str) -> bool:
    """
    快速判断单行是否为 boilerplate（噪音内容）。
    """
    s = line.strip()
    if not s or len(s) < 3:
        return True
    if _LINE_SEP_RE.match(s):
        return True
    if len(s) < 10 and _LINE_FOREIGN_RE.match(s):
        return True
    return False


def _score_line(line: str) -> float:
    """
    给单行文本打分（0-1），分数越高越可能是正文。
    """
    s = line.strip()
    if not s:
        return 0.0
    n = len(s)

    if n < 5:
        return 0.1
    elif n < 15:
        ls = 0.2
    elif n < 30:
        ls = 0.5
    elif n < 200:
        ls = 0.8
    else:
        ls = 0.6

    links = _LINE_LINK_RE.findall(line)
    link_len = sum(len(_LINK_STRIP_RE.sub('', m)) for m in links)
    density = link_len / n if n > 0 else 0

    cn = len(_LINE_CN_RE.findall(s))
    cn_ratio = cn / n if n > 0 else 0

    foreign = len(_LINE_FOREIGN_COUNT_RE.findall(s))
    f_ratio = foreign / n if n > 0 else 0

    score = ls * 0.2 + (1 - density) * 0.2 + cn_ratio * 0.3 + (1 - f_ratio) * 0.15

    if _LINE_PUNCT_RE.search(s):
        score += 0.1

    return max(0.0, min(1.0, score))


def clean_boilerplate_text(text: str, min_score: float = 0.25) -> str:
    """
    对提取后的纯文本进行 boilerplate 清理。

    流程：
    1. 快速噪音行过滤
    2. 行评分过滤（低于 min_score 丢弃）
    3. 连续重复行去重
    4. BOILERPLATE_PATTERNS 正则清理
    5. 多余空行压缩
    """
    if not text:
        return text

    lines = text.split('\n')
    cleaned = []
    prev = ""

    for line in lines:
        s = line.strip()
        if is_boilerplate_line(s):
            continue
        if _score_line(s) < min_score:
            continue
        if s == prev:
            continue
        cleaned.append(line)
        prev = s

    text = '\n'.join(cleaned)

    for bp_re, _ in BOILERPLATE_PATTERNS:
        text = bp_re.sub('', text)

    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def _is_boilerplate_para(text: str) -> bool:
    """判断段落是否为 boilerplate（用于正则提取阶段）"""
    t = text.strip()
    if not t:
        return True
    if re.match(r'\[.+\]\(https?://', t) or t.startswith('http'):
        return True
    if _BP_DATE_RE.match(t) and len(t) < 30:
        return True
    return False