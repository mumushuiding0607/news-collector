"""
bump_version.py - 递增版本号（每次 build_app.bat 自动调用）

行为：
  - metadata.json 的 version_code +1（必做）
  - metadata.json 的 version_name patch 段 +1（默认联动，始终进行）
  - 同步 backend/config.json 的 app_version.latest_build / latest_version
  - --skip-name：跳过 version_name 联动（用于 hotfix / 同版本重试）
  - SKIP_BUMP=1：跳过本次递增（调试 / 失败重试同版本）

约束：
  - version_name 的 patch 段默认跟随 version_code 联动（保持二者一致）
  - 失败构建不回滚 —— versionCode 允许出现间隙，问题不大

Usage:
    python bump_version.py                  # +1 version_code AND version_name.patch
    python bump_version.py --skip-name      # +1 version_code only
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent  # news-collector/
METADATA = ROOT / "publish" / "metadata.json"
CONFIG = ROOT / "backend" / "config.json"


def bump_patch(version_name: str) -> str:
    parts = version_name.split(".")
    if len(parts) != 3:
        raise ValueError(f"version_name 不是 semver 三段式: {version_name}")
    parts[2] = str(int(parts[2]) + 1)
    return ".".join(parts)


def main() -> int:
    if os.environ.get("SKIP_BUMP") == "1":
        print("[bump] SKIP_BUMP=1，跳过本次递增")
        return 0

    skip_name = "--skip-name" in sys.argv

    md = json.loads(METADATA.read_text(encoding="utf-8"))
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))

    old_code = md["version_code"]
    new_code = old_code + 1
    md["version_code"] = new_code

    old_name = md["version_name"]
    new_name = bump_patch(old_name) if not skip_name else old_name
    md["version_name"] = new_name

    # 单一来源：metadata.json 改了 → backend/config.json 同步
    cfg.setdefault("app_version", {})
    cfg["app_version"]["latest_build"] = new_code
    cfg["app_version"]["latest_version"] = new_name

    METADATA.write_text(json.dumps(md, ensure_ascii=False, indent=2), encoding="utf-8")
    CONFIG.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[bump] version_code: {old_code} -> {new_code}")
    if skip_name:
        print(f"[bump] version_name: unchanged ({old_name})")
    else:
        print(f"[bump] version_name: {old_name} -> {new_name}")
    print(f"[bump] synced backend/config.json: latest_build={new_code}, latest_version={new_name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())