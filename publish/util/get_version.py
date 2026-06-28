#!/usr/bin/env python3
"""从 metadata.json 读取版本信息，供批处理脚本调用"""
import json
import sys
from pathlib import Path

meta = Path(__file__).resolve().parent.parent / "metadata.json"
data = json.loads(meta.read_text(encoding="utf-8"))

key = sys.argv[1] if len(sys.argv) > 1 else "version_name"
if key == "version_name":
    print(data["version_name"])
elif key == "version_code":
    print(data["version_code"])
else:
    print(data.get(key, ""), end="")