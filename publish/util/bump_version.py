"""
bump_version.py - 递增版本号并同步到所有配置文件

单一数据源：metadata.json

行为：
  - metadata.json 的 version_code +1
  - metadata.json 的 version_name patch 段 +1（默认联动）
  - 同步到 pubspec.yaml、backend/config.json
  - --skip-name：跳过 version_name 联动
  - SKIP_BUMP=1：跳过本次递增

Usage:
    python bump_version.py                  # +1 version_code AND version_name.patch
    python bump_version.py --skip-name      # +1 version_code only
"""
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent  # news-collector/
METADATA = ROOT / "publish" / "metadata.json"
PUBSPEC = ROOT / "news_board_app" / "pubspec.yaml"
CONFIG = ROOT / "backend" / "config.json"
ANDROID_MANIFEST = ROOT / "news_board_app" / "android" / "app" / "src" / "main" / "AndroidManifest.xml"


def bump_patch(version_name: str) -> str:
    parts = version_name.split(".")
    if len(parts) != 3:
        raise ValueError(f"version_name 不是 semver 三段式: {version_name}")
    parts[2] = str(int(parts[2]) + 1)
    return ".".join(parts)


def sync_pubspec(version, build):
    """更新 pubspec.yaml 的 version 字段（格式：versionName+versionCode）"""
    content = PUBSPEC.read_text(encoding="utf-8")
    # Flutter pubspec.yaml 格式必须是 versionName+versionCode，如 "1.0.46+46"
    content = re.sub(r"^version:\s*\S+$", f"version: {version}+{build}", content, flags=re.MULTILINE)
    PUBSPEC.write_text(content, encoding="utf-8")
    print(f"[bump] pubspec.yaml -> version: {version}+{build}")


def sync_config_json(version, build):
    """更新 backend/config.json 的 app_version"""
    data = json.loads(CONFIG.read_text(encoding="utf-8"))
    data.setdefault("app_version", {})
    data["app_version"]["latest_version"] = version
    data["app_version"]["latest_build"] = build
    CONFIG.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[bump] backend/config.json -> latest_version={version}, latest_build={build}")


def sync_android_manifest(version, build):
    """更新 AndroidManifest.xml 的 versionName 和 versionCode"""
    content = ANDROID_MANIFEST.read_text(encoding="utf-8")
    content = re.sub(
        r'android:versionName="[^"]*"',
        f'android:versionName="{version}"',
        content
    )
    content = re.sub(
        r'android:versionCode="\d+"',
        f'android:versionCode="{build}"',
        content
    )
    ANDROID_MANIFEST.write_text(content, encoding="utf-8")
    print(f"[bump] AndroidManifest.xml -> versionName={version}, versionCode={build}")


def main() -> int:
    if os.environ.get("SKIP_BUMP") == "1":
        print("[bump] SKIP_BUMP=1，跳过本次递增")
        return 0

    skip_name = "--skip-name" in sys.argv

    md = json.loads(METADATA.read_text(encoding="utf-8"))

    old_code = md["version_code"]
    new_code = old_code + 1
    md["version_code"] = new_code

    old_name = md["version_name"]
    new_name = bump_patch(old_name) if not skip_name else old_name
    md["version_name"] = new_name

    METADATA.write_text(json.dumps(md, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[bump] metadata.json: version_code {old_code} -> {new_code}")
    if skip_name:
        print(f"[bump] metadata.json: version_name unchanged ({old_name})")
    else:
        print(f"[bump] metadata.json: version_name {old_name} -> {new_name}")

    # 同步到其他配置文件
    sync_pubspec(new_name, new_code)
    sync_config_json(new_name, new_code)
    sync_android_manifest(new_name, new_code)

    return 0


if __name__ == "__main__":
    sys.exit(main())
