#!/usr/bin/env python3
"""同步 publish/metadata.json 版本到 pubspec.yaml 和 backend/config.json

Single source of truth: publish/metadata.json (version_name, version_code)
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
METADATA = ROOT / "publish" / "metadata.json"
PUBSPEC = ROOT / "news_board_app" / "pubspec.yaml"
CONFIG_JSON = ROOT / "backend" / "config.json"


def get_version_from_metadata():
    """从 metadata.json 读取 version_name 和 version_code"""
    import json
    data = json.loads(METADATA.read_text(encoding="utf-8"))
    return data["version_name"], int(data["version_code"])


def update_pubspec(version):
    """更新 pubspec.yaml 的 version 字段"""
    content = PUBSPEC.read_text(encoding="utf-8")
    content = re.sub(r"^version:\s*\S+$", f"version: {version}", content, flags=re.MULTILINE)
    PUBSPEC.write_text(content, encoding="utf-8")
    print(f"[sync_version] pubspec.yaml -> version: {version}")


def update_config_json(version, build):
    """更新 backend/config.json 的 app_version"""
    import json
    data = json.loads(CONFIG_JSON.read_text(encoding="utf-8"))
    if "app_version" not in data:
        data["app_version"] = {}
    data["app_version"]["latest_version"] = version
    data["app_version"]["latest_build"] = build
    CONFIG_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[sync_version] backend/config.json -> latest_version={version}, latest_build={build}")


def main():
    version, build = get_version_from_metadata()
    update_pubspec(version)
    update_config_json(version, build)
    print(f"[sync_version] all done.")


if __name__ == "__main__":
    main()