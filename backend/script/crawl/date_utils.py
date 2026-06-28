# date_utils.py - 日期提取工具

from script.common.util import parse_publish_time


def extract_date_from_context(title: str, line: str, link_end: int, lines: list, line_idx: int):
    """从标题、链接后文本、后续行中提取日期"""
    found = parse_publish_time(title)
    if found:
        return found
    after_link = line[link_end:].strip()
    if after_link:
        found = parse_publish_time(after_link)
        if found:
            return found
    for look in range(1, 4):
        if line_idx + look >= len(lines):
            break
        cand = lines[line_idx + look].strip()
        if '](' in cand:
            continue
        found = parse_publish_time(cand)
        if found:
            return found
    return None