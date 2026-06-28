"""
update_config_helper.py - 远端 config.json 局部字段更新工具

被 update_version.bat 调用，替代 cmd heredoc（cmd 的 (...) 块会被字符串内的
括号意外切断，导致 python 脚本不完整）。

Usage:
    python update_config_helper.py <config_path> <version> <build> <desc>
"""
import json
import sys


def main():
    if len(sys.argv) != 5:
        print(f"Usage: {sys.argv[0]} <config_path> <version> <build> <desc>", file=sys.stderr)
        sys.exit(2)

    config_path, new_version, new_build_str, update_desc = sys.argv[1:5]
    new_build = int(new_build_str)

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    config.setdefault("app_version", {})
    config["app_version"]["latest_version"] = new_version
    config["app_version"]["latest_build"] = new_build
    config["app_version"]["update_description"] = update_desc

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    print("Config updated successfully")


if __name__ == "__main__":
    main()
