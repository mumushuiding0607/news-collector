"""
jsonutil.py - JSON 处理工具
"""
import json


def parse_json_field(value: str | dict | None) -> dict | None:
    """
    解析 JSON 字段，支持字符串或已解析的 dict。

    Returns:
        dict 或 None（解析失败时）
    """
    if value is None:
        return None
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except Exception:
            return None
    return None


def write_json(data: dict, path, indent: int = 2) -> None:
    """写入 JSON 文件（UTF-8，ensure_ascii=False）"""
    from pathlib import Path
    path = Path(path)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=indent), encoding="utf-8")
