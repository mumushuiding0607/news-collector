#!/usr/bin/env python3
"""
Sync app_icon.png from publish folder to Android res folder.
Run before Flutter APK build to update the app icon.
"""
import sys
import shutil
from pathlib import Path

def sync_icon():
    script_dir = Path(__file__).resolve().parent
    # scripts -> news_board_app
    project_root = script_dir.parent
    # news_board_app/publish
    publish_dir = project_root / "publish"
    # news_board_app/android/app/src/main/res
    res_dir = project_root / "android" / "app" / "src" / "main" / "res"

    # Source icon
    src_icon = publish_dir / "app_icon.png"
    if not src_icon.exists():
        print(f"[sync_icon] WARNING: {src_icon} not found, skipping icon sync")
        return 0

    # Destination
    dst_foreground = res_dir / "drawable" / "ic_launcher_foreground.png"

    # Ensure destination directory exists
    dst_foreground.parent.mkdir(parents=True, exist_ok=True)

    # Copy icon
    shutil.copy2(src_icon, dst_foreground)
    print(f"[sync_icon] Synced: {src_icon} -> {dst_foreground}")

    return 0

if __name__ == "__main__":
    sys.exit(sync_icon())
