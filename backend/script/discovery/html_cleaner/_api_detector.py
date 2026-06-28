"""
_api_detector.py - API 检测模块
"""

from __future__ import annotations

import re

from ._constants import (
    _SCRIPT_TAG_RE,
    _AJAX_CONFIG_PATTERN,
    _AJAX_URL_PATTERN,
    _AJAX_TYPE_PATTERN,
    _AJAX_DATATYPE_PATTERN,
    _AJAX_JSONP_CALLBACK,
    _AJAX_PARAMS_PATTERN,
    _JQ_SIMPLE_PATTERN,
    _FETCH_PATTERN,
    _URL_VAR_PATTERN,
    _CNTV_API_PATTERN,
)
from ._types import ApiEndpoint


def _parse_ajax_call(full: str, cfg: str) -> ApiEndpoint | None:
    """解析 $.ajax() 配置字符串"""
    um = _AJAX_URL_PATTERN.search(cfg)
    if not um:
        return None
    url = um.group(1) if um.group(1) else f'<variable: {um.group(2)}>'
    tm = _AJAX_TYPE_PATTERN.search(cfg)
    method = tm.group(1) if tm else 'get'
    dtm = _AJAX_DATATYPE_PATTERN.search(cfg)
    dtype = dtm.group(1) if dtm else 'json'
    if _AJAX_JSONP_CALLBACK.search(cfg):
        dtype = 'jsonp'
    params = list(set(_AJAX_PARAMS_PATTERN.findall(cfg)))
    return ApiEndpoint(url=url, method=f'$.ajax({method})', data_type=dtype,
                       params=params, raw_snippet=full[:300])


def detect_apis_in_html(html: str) -> list[ApiEndpoint]:
    """检测 HTML 中的 API 调用模式"""
    apis = []
    for script_content in _SCRIPT_TAG_RE.findall(html):
        if not script_content.strip():
            continue

        for m in _AJAX_CONFIG_PATTERN.finditer(script_content):
            api = _parse_ajax_call(m.group(0), m.group(1))
            if api:
                apis.append(api)

        for m in _JQ_SIMPLE_PATTERN.finditer(script_content):
            apis.append(ApiEndpoint(
                url=m.group(2), method=f'$.{m.group(1)}',
                data_type='json', params=[], raw_snippet=m.group(0)[:200]
            ))

        for m in _FETCH_PATTERN.finditer(script_content):
            apis.append(ApiEndpoint(
                url=m.group(1), method='fetch',
                data_type='json', params=[], raw_snippet=m.group(0)[:200]
            ))

        for m in _URL_VAR_PATTERN.finditer(script_content):
            raw = m.group(1)
            cleaned = re.sub(r'\s*\+\s*["\'][^"\']*["\']\s*', '/', raw)
            cleaned = re.sub(r'\s*\+\s*\w+\s*', '', cleaned)
            if 'api' in cleaned.lower() or '/list' in cleaned.lower() or '/news' in cleaned.lower():
                apis.append(ApiEndpoint(
                    url=cleaned, method='url_var',
                    data_type='jsonp', params=[], raw_snippet=raw[:200]
                ))

        for m in _CNTV_API_PATTERN.finditer(script_content):
            url = m.group(0)
            start = max(0, m.start() - 200)
            end = min(len(script_content), m.end() + 50)
            apis.append(ApiEndpoint(
                url='//' + url, method='$.ajax',
                data_type='jsonp', params=['id', 'n', 'sort', 'p', 'bd', 'mode', 'serviceId'],
                raw_snippet=script_content[start:end][:300]
            ))

    return apis