"""
iwencai - 同花顺问财查询模块

根据自然语言问句查询A股、指数数据。

功能：
  - 根据自然语言问句查询A股、指数数据
  - 支持指定查询类型（板块/指数 或 个股）
  - 支持分页查询（可获取超过100条的数据）
  - 返回结构化JSON数据
  - 自动处理请求头和Token

安装依赖：
  pip install requests

示例：
  from iwencai import query_wencai

  # 查询板块涨跌（默认100条）
  result = query_wencai("板块涨跌幅排名")

  # 查询200条数据 (page=2, loop=2)
  result = query_wencai("个股涨跌幅排行", page=1, perpage=100, loop=2)

  # 查询个股DDE
  result = query_wencai("个股DDE排行", secondary_intent="stock")

  # 查询指定板块
  result = query_wencai("油气开采及服务板块行情", secondary_intent="zhishu")
"""

import json
import re
import math
import subprocess
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse, parse_qs

import requests


# ==================== 配置 ====================

# 获取模块所在目录
MODULE_DIR = Path(__file__).parent
CACHE_FILE = MODULE_DIR / "wencai_headers.json"
BUNDLE_FILE = MODULE_DIR / "hexin-v.bundle.cjs"

# API地址
ROBOT_DATA_URL = "https://www.iwencai.com/customized/chart/get-robot-data"
GET_DATA_LIST_URL = "https://www.iwencai.com/gateway/urp/v7/landing/getDataList"

# Token缓存有效期（24小时）
TOKEN_MAX_AGE = 24 * 60 * 60 * 1000

# ==================== Token和Headers管理 ====================

TIMESTAMP_PATTERN = re.compile(r"\[\d{8}(\s\d{2}:\d{2}:\d{2})?(-\d{8}(\s\d{2}:\d{2}:\d{2})?)?\]")
CLEAN_PATTERN = re.compile(r"[{}()\[\]/\\\-*%=<>!@#$&^]+")
CORE_NAME_EXTRACT = re.compile(r"[\u4e00-\u9fa5a-zA-Z0-9]+")


def _ensure_cache_dir():
    """确保缓存目录存在"""
    if not MODULE_DIR.exists():
        MODULE_DIR.mkdir(parents=True, exist_ok=True)


def _load_headers_from_cache() -> dict | None:
    """从缓存加载headers"""
    try:
        _ensure_cache_dir()
        if CACHE_FILE.exists():
            data = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
            if data.get("headers") and data.get("time"):
                age = datetime.now().timestamp() * 1000 - data["time"]
                if age < TOKEN_MAX_AGE:
                    return data["headers"]
    except Exception:
        pass
    return None


def _save_headers_to_cache(headers: dict):
    """保存headers到缓存"""
    try:
        _ensure_cache_dir()
        data = {
            "headers": headers,
            "time": datetime.now().timestamp() * 1000,
            "date": datetime.now().isoformat(),
        }
        CACHE_FILE.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def _get_token() -> str:
    """从hexin-v.bundle.cjs获取token"""
    try:
        result = subprocess.run(
            ["node", str(BUNDLE_FILE)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.stdout.strip()
    except Exception:
        return ""


def _get_random_user_agent() -> str:
    """随机获取User-Agent"""
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    ]
    import random
    return random.choice(user_agents)


def get_headers(force_refresh: bool = False) -> dict:
    """
    获取请求头

    Args:
        force_refresh: 是否强制刷新token

    Returns:
        dict: 包含hexin-v和User-Agent的请求头
    """
    if not force_refresh:
        cached = _load_headers_from_cache()
        if cached:
            return cached

    headers = {
        "hexin-v": _get_token(),
        "User-Agent": _get_random_user_agent(),
    }
    _save_headers_to_cache(headers)
    return headers


# ==================== 辅助函数 ====================

def _extract_core_indicator_name(field_name: str) -> str:
    """
    从字段名中提取核心指标名称
    移除日期时间（支持 [YYYYMMDD] 和 [YYYYMMDD HH:MM:SS-HH:MM:SS] 等格式）、
    括号、斜杠等非核心字符
    """
    # 移除时间标记
    without_timestamp = TIMESTAMP_PATTERN.sub("", field_name)
    # 移除干扰符号
    cleaned = CLEAN_PATTERN.sub("", without_timestamp)
    # 提取连续的中文、字母、数字
    core_parts = CORE_NAME_EXTRACT.findall(cleaned)
    return "".join(core_parts)


def _is_key_match_core(full_key: str, core_name: str) -> bool:
    """
    判断完整的数据键是否与核心指标名称匹配
    """
    key_core = _extract_core_indicator_name(full_key)

    # 1. 完全匹配
    if key_core == core_name:
        return True

    # 2. 处理括号后缀的情况：如 "市盈率pe" 匹配 "市盈率"
    bracket_suffix_pattern = re.compile(r"[a-zA-Z]+$")
    key_core_without_suffix = bracket_suffix_pattern.sub("", key_core)
    if key_core_without_suffix == core_name:
        return True

    # 3. 反向处理：输入带后缀但API返回不带后缀的情况
    core_name_without_suffix = bracket_suffix_pattern.sub("", core_name)
    if core_name_without_suffix and key_core == core_name_without_suffix:
        return True

    return False


def _get_dynamic_field(item: dict, field_prefix: str):
    """
    智能获取字段值，适用于字段名复杂、日期位置不定的情况
    """
    # 1. 标准情况：直接匹配成功
    if field_prefix in item:
        return item[field_prefix]

    # 2. 智能提取核心名，用于后续模糊匹配
    core_name = _extract_core_indicator_name(field_prefix)

    # 3. 在数据键中寻找包含核心名的项
    for key in item:
        if _is_key_match_core(key, core_name):
            return item[key]

    return None


def _format_change_rate(value) -> str:
    """格式化涨跌幅"""
    if not value and value != 0:
        return ""
    num = float(value)
    sign = "+" if num > 0 else ""
    return f"{sign}{num:.2f}%"


def _safe_round(value, decimals: int = 2):
    """安全四舍五入"""
    if not value and value != 0:
        return None
    try:
        num = float(value)
        return round(num, decimals)
    except (ValueError, TypeError):
        return None


def _parse_url_params(url: str) -> dict:
    """解析URL参数为字典"""
    if not url:
        return {}
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    # 转换列表为单个值
    return {k: v[0] if isinstance(v, list) and len(v) == 1 else v for k, v in params.items()}


# ==================== 核心查询功能 ====================

def _get_condition(question: str, secondary_intent: str, headers: dict) -> dict | None:
    """
    获取condition和分页参数（第一步）

    Returns:
        dict: 包含 condition, url_params, row_count 等
    """
    data = {
        "add_info": "{\"urp\":{\"scene\":1,\"company\":1,\"business\":1},\"contentType\":\"json\",\"searchInfo\":true}",
        "perpage": 10,
        "page": 1,
        "source": "Ths_iwencai_Xuangu",
        "log_info": "{\"input_type\":\"click\"}",
        "version": "2.0",
        "secondary_intent": secondary_intent,
        "question": question,
    }

    encoded_question = requests.utils.quote(question)
    request_headers = {
        **headers,
        "Origin": "https://www.iwencai.com",
        "Referer": f"https://www.iwencai.com/unifiedwap/result?w={encoded_question}",
    }

    try:
        response = requests.post(
            ROBOT_DATA_URL,
            json=data,
            headers=request_headers,
            timeout=30,
        )
        result = response.json()

        status_code = result.get("status_code", result.get("status", -1))
        if status_code != 0:
            return None

        # 提取condition和url
        content = result.get("data", {}).get("answer", [{}])[0].get("txt", [{}])[0].get("content", {})
        if isinstance(content, str):
            content = json.loads(content)

        components = content.get("components", [])
        if not components:
            return None

        # 获取footer_info中的url
        footer_url = components[0].get("config", {}).get("other_info", {}).get("footer_info", {}).get("url", "")

        return {
            "condition": components[0].get("data", {}).get("meta", {}).get("extra", {}).get("condition"),
            "url_params": _parse_url_params(footer_url),
            "row_count": components[0].get("data", {}).get("meta", {}).get("extra", {}).get("row_count", 0),
        }
    except Exception:
        return None


def _fetch_page(url_params: dict, page: int, perpage: int, headers: dict, question: str) -> list | None:
    """
    获取单页数据（第二步）

    Args:
        url_params: 从第一步获取的url参数
        page: 页码
        perpage: 每页数量
        headers: 请求头
        question: 原始问题（用于Referer）

    Returns:
        list: 数据列表，失败返回None
    """
    data = {
        **url_params,
        "page": page,
        "perpage": perpage,
    }

    encoded_question = requests.utils.quote(question)
    request_headers = {
        **headers,
        "Origin": "https://www.iwencai.com",
        "Referer": f"https://www.iwencai.com/unifiedwap/result?w={encoded_question}",
    }

    try:
        response = requests.post(
            GET_DATA_LIST_URL,
            data=data,
            headers=request_headers,
            timeout=30,
        )
        result = response.json()

        # 从 answer.components[0].data.datas 获取数据
        datas = (
            result.get("answer", {})
            .get("components", [{}])[0]
            .get("data", {})
            .get("datas", [])
        )

        if not datas:
            return None
        return datas
    except Exception:
        return None


def query_wencai(
    question: str,
    secondary_intent: str | None = None,
    page: int = 1,
    perpage: int = 100,
    loop: int = 1,
) -> dict:
    """
    查询同花顺问财数据（支持分页查询）

    Args:
        question: 查询问句
        secondary_intent: 查询类型，可选 "zhishu" (板块/指数) 或 "stock" (个股)
                         如果不指定，会根据问句内容自动判断
        page: 起始页码（默认1）
        perpage: 每页数量（默认100）
        loop: 循环次数（用于获取更多数据，默认1）

    Returns:
        dict: 包含查询结果的字典，结构如下：
        {
            "status": "success" | "error",
            "question": str,
            "secondary_intent": "zhishu" | "stock",
            "total_count": int,
            "data": list[dict],
            "timestamp": str,
            "message": str  # 仅在status为error时
        }

    示例：
        >>> result = query_wencai("板块涨跌幅排名")
        >>> print(result["data"][0])
        {
            "code": "881001",
            "name": "银行",
            "change_rate": "+2.35%",
            "turnover": "2.15",
            ...
        }

        >>> # 获取200条数据
        >>> result = query_wencai("个股涨跌幅排行", page=1, perpage=100, loop=2)
    """
    # 如果用户指定了 secondary_intent，使用用户指定的值；否则自动判断
    if not secondary_intent:
        if "指数" in question or "板块" in question:
            secondary_intent = "zhishu"
        else:
            secondary_intent = "stock"

    headers = get_headers()

    # 如果loop > 1，使用分页查询
    if loop > 1:
        # 第一步：获取condition
        params = _get_condition(question, secondary_intent, headers)
        if not params or not params.get("condition"):
            # fallback到原来的方式
            return _query_wencai_simple(question, secondary_intent, page, perpage, loop, headers)

        all_datas = []
        max_page = math.ceil(params["row_count"] / perpage) if params["row_count"] else loop
        loop_count = min(loop, max_page)

        for i in range(loop_count):
            current_page = page + i
            datas = _fetch_page(params["url_params"], current_page, perpage, headers, question)
            if not datas:
                break
            all_datas.extend(datas)

            if len(datas) < perpage:
                break
    else:
        # 简单模式，直接查询
        return _query_wencai_simple(question, secondary_intent, page, perpage, loop, headers)

    # 简化数据格式
    simplified_data = _simplify_data(all_datas, secondary_intent)

    return {
        "status": "success",
        "question": question,
        "secondary_intent": secondary_intent,
        "total_count": len(simplified_data),
        "data": simplified_data,
        "timestamp": datetime.now().isoformat(),
    }


def _query_wencai_simple(question: str, secondary_intent: str, page: int, perpage: int, loop: int, headers: dict) -> dict:
    """简单查询模式（不分页，直接从get-robot-data获取数据）"""
    all_datas = []

    for i in range(loop):
        current_page = page + i

        data = {
            "source": "Ths_iwencai_Xuangu",
            "version": "2.0",
            "query_area": "",
            "block_list": "",
            "question": question,
            "perpage": perpage,
            "page": current_page,
            "secondary_intent": secondary_intent,
            "add_info": json.dumps({
                "urp": {"scene": 1, "company": 1, "business": 1},
                "contentType": "json",
                "searchInfo": True,
            }),
            "log_info": json.dumps({"input_type": "typewrite"}),
        }

        encoded_question = requests.utils.quote(question)
        request_headers = {
            **headers,
            "Origin": "https://www.iwencai.com",
            "Referer": f"https://www.iwencai.com/unifiedwap/result?w={encoded_question}",
        }

        try:
            response = requests.post(ROBOT_DATA_URL, json=data, headers=request_headers, timeout=30)
            result = response.json()

            status_code = result.get("status_code", result.get("status", -1))
            if status_code != 0:
                return {
                    "status": "error",
                    "code": f"API_ERROR_{status_code}",
                    "message": result.get("status_msg") or "API返回错误",
                }

            # 提取数据
            datas = (
                result.get("data", {})
                .get("answer", [{}])[0]
                .get("txt", [{}])[0]
                .get("content", {})
                .get("components", [{}])[0]
                .get("data", {})
                .get("datas", [])
            )
            all_datas.extend(datas)

            if len(datas) < perpage:
                break
        except Exception as e:
            return {"status": "error", "code": "REQUEST_FAILED", "message": str(e)}

    simplified_data = _simplify_data(all_datas, secondary_intent)

    return {
        "status": "success",
        "question": question,
        "secondary_intent": secondary_intent,
        "total_count": len(simplified_data),
        "data": simplified_data,
        "timestamp": datetime.now().isoformat(),
    }


def _simplify_data(all_datas: list, secondary_intent: str) -> list:
    """简化数据格式"""
    simplified_data = []

    for item in all_datas:
        if secondary_intent == "zhishu":
            change_rate = _get_field(item, "指数@涨跌幅:前复权")
            simplified_data.append({
                "code": item.get("code") or item.get("指数代码") or "",
                "name": item.get("指数简称") or item.get("name") or "",
                "change_rate": f"{float(change_rate):.2f}%" if change_rate else "",
                "turnover": _get_field(item, "指数@换手率") or "",
                "volume": _get_field(item, "指数@成交量") or "",
                "amount": _get_field(item, "指数@成交额") or "",
                "dde_net_amount": _get_field(item, "指数@dde大单净额") or "",
                "dde_intensity": _get_field(item, "指数@dde大单净额{/}指数@流通市值{*}10000") or "",
                "advancers": _get_field(item, "指数@上涨家数") or 0,
                "decliners": _get_field(item, "指数@下跌家数") or 0,
                "limit_up": _get_field(item, "指数@涨停家数") or 0,
                "limit_down": _get_field(item, "指数@跌停家数") or 0,
            })
        else:
            change_rate_val = _get_dynamic_field(item, "最新涨跌幅") or _get_dynamic_field(item, "涨跌幅:前复权")
            simplified_data.append({
                "code": item.get("code") or item.get("代码") or "",
                "name": item.get("name") or item.get("股票简称") or "",
                "market_code": item.get("market_code") or "",
                "price": item.get("price") or item.get("最新价") or "",
                "change_rate": _format_change_rate(change_rate_val) if change_rate_val else "",
                "dde_net_amount": _get_dynamic_field(item, "dde大单净额") or "",
                "industrys": _get_dynamic_field(item, "所属同花顺行业") or "",
                "turnover_rate": _get_dynamic_field(item, "换手率") or "",
                "volume_ratio": _get_dynamic_field(item, "量比") or "",
            })

    # 按涨跌幅降序排序
    simplified_data.sort(
        key=lambda x: float(x["change_rate"].rstrip("%").lstrip("+")) if x["change_rate"] else 0,
        reverse=True,
    )

    return simplified_data


def _get_field(item: dict, prefix: str):
    """获取字段值，精确匹配字段名前缀，排除排名字段"""
    for key in item:
        if key.startswith(prefix) and "排名" not in key:
            return item[key]
    return None


# ==================== CLI入口 ====================

def main():
    """命令行入口"""
    import sys

    args = sys.argv[1:]
    question = ""
    secondary_intent = None
    page = 1
    perpage = 100
    loop = 1

    i = 0
    while i < len(args):
        arg = args[i]
        if arg in ("--secondary-intent", "-s"):
            if i + 1 < len(args) and not args[i + 1].startswith("-"):
                secondary_intent = args[i + 1]
                i += 2
            else:
                i += 1
            continue
        if arg in ("--page", "-p"):
            if i + 1 < len(args):
                page = int(args[i + 1])
                i += 2
            else:
                i += 1
            continue
        if arg in ("--perpage", "-n"):
            if i + 1 < len(args):
                perpage = int(args[i + 1])
                i += 2
            else:
                i += 1
            continue
        if arg in ("--loop", "-l"):
            if i + 1 < len(args):
                loop = int(args[i + 1])
                i += 2
            else:
                i += 1
            continue
        if arg.startswith("-"):
            i += 1
            continue
        if question:
            question += " "
        question += arg
        i += 1

    if not question:
        print("用法: python -m iwencai \"查询问句\" [选项]")
        print("")
        print("参数:")
        print("  -s, --secondary-intent  指定查询类型 (zhishu=板块/指数, stock=个股)")
        print("  -p, --page              起始页码 (默认1)")
        print("  -n, --perpage           每页数量 (默认100)")
        print("  -l, --loop              循环次数/页数 (默认1)")
        print("")
        print("示例:")
        print("  python -m iwencai \"板块涨跌幅排名\"")
        print("  python -m iwencai \"个股涨跌幅排行\" -s stock")
        print("  python -m iwencai \"个股涨跌幅排行\" -s stock -l 2  # 获取200条")
        sys.exit(1)

    result = query_wencai(question, secondary_intent=secondary_intent, page=page, perpage=perpage, loop=loop)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()