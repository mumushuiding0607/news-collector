"""
日期时间解析工具 & 文章内容质量检查
"""
import re
from datetime import datetime, date


# 整合后的日期时间正则（覆盖所有常见格式）
COMBINED_DATE_REGEX = re.compile(
    r'(?P<iso>(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})T(\d{1,2}):(\d{2}):(\d{2})(?:\.\d+)?)'
    r'|(?P<num>(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})(?:\s+(\d{1,2}):(\d{2})(?::(\d{2}))?)?)'
    r'|(?P<cn>(\d{4})年(\d{1,2})月(\d{1,2})日(?:\s*(\d{1,2}):(\d{2})(?::(\d{2}))?)?)'
    r'|(?P<en>(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},\s+\d{4})'
    r'|(?P<us>(\d{1,2})/(\d{1,2})/(\d{4}))'
)


def parse_publish_time(text: str) -> str | None:
    """从文本中提取并解析日期时间，返回最晚的有效日期（而非第一个）"""
    if not text:
        return None
    all_dates = []
    for m in COMBINED_DATE_REGEX.finditer(text):
        groups = m.groupdict()
        dt_candidate = None
        if groups['iso']:
            dt_str = re.sub(r'(\d{2}:\d{2}:\d{2})\.\d+$', r'\1', groups['iso'])
            try:
                dt_candidate = datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%S")
            except ValueError:
                continue
        elif groups['num']:
            dt_str = groups['num']
            dt_str = re.sub(r'(\d{2}:\d{2}:\d{2})\.\d+$', r'\1', dt_str)
            if re.search(r'\d{1,2}:\d{2}', dt_str):
                for fmt in ["%Y-%m-%d %H:%M:%S","%Y-%m-%d %H:%M","%Y/%m/%d %H:%M:%S","%Y/%m/%d %H:%M","%Y.%m.%d %H:%M:%S","%Y.%m.%d %H:%M"]:
                    try:
                        dt_candidate = datetime.strptime(dt_str, fmt)
                        break
                    except ValueError:
                        continue
            else:
                for fmt in ["%Y-%m-%d","%Y/%m/%d","%Y.%m.%d"]:
                    try:
                        dt_candidate = datetime.strptime(dt_str, fmt)
                        break
                    except ValueError:
                        continue
        elif groups['cn']:
            dt_str = groups['cn']
            if re.search(r'\d{1,2}:\d{2}', dt_str):
                for fmt in ["%Y年%m月%d日%H:%M:%S","%Y年%m月%d日 %H:%M:%S","%Y年%m月%d日%H:%M","%Y年%m月%d日 %H:%M"]:
                    try:
                        dt_candidate = datetime.strptime(dt_str, fmt)
                        break
                    except ValueError:
                        continue
            else:
                try:
                    dt_candidate = datetime.strptime(dt_str, "%Y年%m月%d日")
                except ValueError:
                    continue
        elif groups['en']:
            dt_str = groups['en']
            try:
                dt_candidate = datetime.strptime(dt_str, "%b %d, %Y")
            except ValueError:
                continue
        elif groups['us']:
            dt_str = groups['us']
            try:
                dt_candidate = datetime.strptime(dt_str, "%m/%d/%Y")
            except ValueError:
                continue
        if dt_candidate:
            all_dates.append(dt_candidate)
    if not all_dates:
        return None
    # 返回最晚的日期
    latest = max(all_dates)
    return latest.strftime("%Y-%m-%d %H:%M:%S")


def is_today(publish_time_str: str | None, today_date: date | None = None) -> bool:
    """判断是否为当天日期"""
    if not publish_time_str:
        return False
    if today_date is None:
        today_date = date.today()
    try:
        pub_date = datetime.strptime(publish_time_str[:10], "%Y-%m-%d").date()
        return pub_date == today_date
    except (ValueError, TypeError):
        return False


def extract_date_from_html(html: str) -> str | None:
    """从 HTML 中提取日期时间，尝试多种策略"""
    if not html:
        return None

    # 策略1：从 news_bt1_left 提取
    bt1 = re.search(r'<div\s+class="news_bt1_left"[^>]*>([\s\S]*?)</div>', html)
    if bt1:
        pub_time = parse_publish_time(bt1.group(1))
        if pub_time:
            return pub_time

    # 策略1.5：从 id="newstime" 提取（人民网等）
    newstime = re.search(r'<b\s+id="newstime"[^>]*>([\s\S]*?)</b>', html)
    if newstime:
        pub_time = parse_publish_time(newstime.group(1))
        if pub_time:
            return pub_time

    # 策略1.6：从 w-createtime-date/time 提取（csia 等）
    createtime = re.search(r'class="[^"]*w-createtime-date[^"]*"[^>]*>\s*([\d-]+)\s*</span>\s*<[^>]*class="[^"]*w-createtime-time[^"]*"[^>]*>\s*([\d:]+)\s*</span>', html)
    if createtime:
        date_str = createtime.group(1).strip()
        time_str = createtime.group(2).strip()
        combined = f"{date_str} {time_str}"
        pub_time = parse_publish_time(combined)
        if pub_time:
            return pub_time

    # 策略1.7：从 detail_left 等类提取（SMM 等）
    detail_left = re.search(r'class="[^"]*detail_left[^"]*"[^>]*>([\s\S]*?)</div>', html)
    if detail_left:
        text = re.sub(r'<[^>]+>', '', detail_left.group(1)).strip()
        pub_time = parse_publish_time(text)
        if pub_time:
            return pub_time

    # 策略2：从 news_info 提取
    info = re.search(r'<div\s+class="news_info"[^>]*>([\s\S]*?)</div>', html)
    if info:
        pub_time = parse_publish_time(info.group(1))
        if pub_time:
            return pub_time

    # 策略3：meta 中的标准时间
    meta_dates = re.findall(r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})', html[:5000])
    for d in meta_dates:
        try:
            dt = datetime.strptime(d, "%Y-%m-%d %H:%M:%S")
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            pass

    # 策略4：datePublished / dateModified / publishdate
    date_meta = re.search(r'(?:datePublished|dateModified|pubdate)[^>]*content="([^"]+)"', html, re.IGNORECASE)
    if date_meta:
        pub_time = parse_publish_time(date_meta.group(1))
        if pub_time:
            return pub_time

    # 策略5：最后兜底：全文本扫描（扩大范围，避免截断导致丢失较晚的日期）
    return parse_publish_time(html[:15000])


def check_article_quality(title: str, content: str, publish_time: str | None) -> dict:
    """
    检查文章内容质量，返回报告字典。
    检查项：
      1. content_length - 正文长度是否足够（>200字符）
      2. has_title - 标题是否存在且非空
      3. has_valid_date - 日期时间是否完整（不是 00:00:00 的疑似缺失）
      4. no_noise_headers - 是否包含疑似噪音标题（如图集、组图、无意义前缀）
      5. content_purity - 正文是否纯净（无大量无关标签字符残留）
    """
    report = {
        "passed": True,
        "issues": [],
        "content_length": len(content),
        "title_length": len(title),
        "has_time": publish_time is not None,
        "time_is_zero": False,
    }

    # 检查1：正文长度
    if len(content) < 200:
        report["passed"] = False
        report["issues"].append(f"content_too_short:{len(content)}")

    # 检查2：标题存在
    if not title or len(title) < 5:
        report["passed"] = False
        report["issues"].append("title_missing_or_too_short")

    # 检查3：时间完整性（时间部分为 00:00:00 可能是缺失）
    if publish_time:
        time_part = publish_time.split(" ")[1] if " " in publish_time else ""
        if time_part == "00:00:00":
            report["time_is_zero"] = True
            report["issues"].append("time_may_be_missing")

    # 检查4：噪音标题
    noise_patterns = [
        r'^[\[【]?(组图|图集|专辑|专题|专栏|视频|图片|海报)[】\]]',
        r'^!\[.*?\]\(',  # markdown图片前缀
        r'^[|\-=]{3,}',    # 分隔线
        r'^\d+$',          # 纯数字标题
    ]
    for pat in noise_patterns:
        if re.match(pat, title.strip()):
            report["passed"] = False
            report["issues"].append(f"noise_title:{pat}")
            break

    # 检查5：正文纯净度 - 残留大量标签符号说明内容提取差
    label_chars = content.count('<') + content.count('>') + content.count('{')
    if label_chars > len(content) * 0.05:  # 标签字符超过5%怀疑不纯净
        report["passed"] = False
        report["issues"].append(f"content_impure:label_chars={label_chars}")

    return report


if __name__ == "__main__":
    # 单元测试
    test_cases = [
        # (input, expected_output)
        # ISO格式
        ("2026-05-27T06:13:00", "2026-05-27 06:13:00"),
        ("2026-05-27T06:13:00.123", "2026-05-27 06:13:00"),
        # 数字格式 - 纯日期
        ("2026-05-27", "2026-05-27 00:00:00"),
        ("2026/05/27", "2026-05-27 00:00:00"),
        ("2026.05.27", "2026-05-27 00:00:00"),
        # 数字格式 - 日期时间（有无空格、有无秒）
        ("2026-05-27 06:13", "2026-05-27 06:13:00"),
        ("2026-05-27 06:13:45", "2026-05-27 06:13:45"),
        ("2026/05/27 06:13", "2026-05-27 06:13:00"),
        ("2026.05.27 06:13:45", "2026-05-27 06:13:45"),
        # 中文格式 - 纯日期
        ("2026年05月27日", "2026-05-27 00:00:00"),
        # 中文格式 - 日期时间（有无空格、有无秒）
        ("2026年05月27日06:13", "2026-05-27 06:13:00"),
        ("2026年05月27日 06:13", "2026-05-27 06:13:00"),
        ("2026年05月27日06:13:45", "2026-05-27 06:13:45"),
        ("2026年05月27日 06:13:45", "2026-05-27 06:13:45"),
        ("2026年05月27日 6:13", "2026-05-27 06:13:00"),
        # 英文格式
        ("Jan 15, 2026", "2026-01-15 00:00:00"),
        # 美式格式
        ("05/27/2026", "2026-05-27 00:00:00"),
        # 无效输入
        ("", None),
        ("no date here", None),
        ("foobar", None),
    ]

    print("=" * 60)
    print("parse_publish_time 单元测试")
    print("=" * 60)
    passed = 0
    failed = 0
    for i, (inp, expected) in enumerate(test_cases):
        result = parse_publish_time(inp)
        ok = result == expected
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] #{i+1:02d}  {inp!r:40s} -> {result}  (expected: {expected})")
        if ok:
            passed += 1
        else:
            failed += 1

    print()
    print("=" * 60)
    print(f"结果: {passed} 通过, {failed} 失败")
    print("=" * 60)