import re

from datetime import datetime, date


# ---------------------------------------------------------------------------
# 整合正则（覆盖所有常见格式）
# ---------------------------------------------------------------------------
COMBINED_DATE_REGEX = re.compile(
    # ISO8601: 2026-05-28T09:15:59 或 2026-05-28T09:15:59.593
    r'(?P<iso>(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})T(\d{1,2}):(\d{2}):(\d{2})(?:\.\d+)?)'
    # 数字格式（年月日，有无时间，有无毫秒）
    r'|(?P<num>(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})(?:\s+(\d{1,2}):(\d{2})(?::(\d{2}))?(?:\.\d+)?)?)'
    # 中文格式（有、无时间，有无毫秒）
    r'|(?P<cn>(\d{4})年(\d{1,2})月(\d{1,2})日(?:\s*(\d{1,2}):(\d{2})(?::(\d{2}))?(?:\.\d+)?)?)'
    r'|(?P<en>(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},\s+\d{4})'
    r'|(?P<us>(\d{1,2})/(\d{1,2})/(\d{4}))'
)


def _normalize_to_iso(date_str: str) -> str | None:
    """
    将任意格式日期字符串规范化为 YYYY-MM-DD HH:MM:SS，
    仅用于比较日期早晚，不改变原始存储值。
    无法解析时返回 None（降级用原始值比较）。
    """
    s = date_str.strip()
    # ISO 原生（包含 T 和空格两种）
    if re.match(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', s):
        return s
    if re.match(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}', s):
        return s[:10] + ' ' + s[11:19]
    if re.match(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$', s):
        return s[:10] + ' 00:00:00'
    # 数字格式：YYYY-MM-DD / YYYY-MM-DD HH:MM:SS / YYYY.MM.DD HH:MM
    m = re.match(r'(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})(?:\s+(\d{1,2}):(\d{2})(?::(\d{2}))?)?', s)
    if m:
        y, mo, d = m.group(1), m.group(2), m.group(3)
        h = m.group(4) or '00'
        mi = m.group(5) or '00'
        sec = m.group(6) or '00'
        try:
            return f"{y}-{int(mo):02d}-{int(d):02d} {int(h):02d}:{int(mi):02d}:{int(sec):02d}"
        except ValueError:
            pass
    # 中文格式：YYYY年MM月DD日 HH:MM:SS
    m = re.match(r'(\d{4})年(\d{1,2})月(\d{1,2})日(?:\s*(\d{1,2}):(\d{2})(?::(\d{2}))?)?', s)
    if m:
        y, mo, d = m.group(1), m.group(2), m.group(3)
        h = m.group(4) or '00'
        mi = m.group(5) or '00'
        sec = m.group(6) or '00'
        try:
            return f"{y}-{int(mo):02d}-{int(d):02d} {int(h):02d}:{int(mi):02d}:{int(sec):02d}"
        except ValueError:
            pass
    return None


def parse_publish_time(text: str) -> str | None:
    """
    从文本中提取日期时间，原始格式存储（无 strptime 转换）。

    流程：
      1. 预处理去掉 JS 毫秒后缀（.593 等）
      2. 正则扫描所有日期匹配
      3. _normalize_to_iso 规范化后字符串比较，取最晚
      4. 返回原始格式字符串（不改变格式）
    """
    if not text:
        return None

    # 注意：不剥离毫秒，原生格式直接存储

    matched = []  # (raw_string, iso_string)
    for m in COMBINED_DATE_REGEX.finditer(text):
        raw = m.group().strip()
        iso = _normalize_to_iso(raw)
        matched.append((raw, iso))

    if not matched:
        return None

    # 用 ISO 规范化字符串比较取最晚，降级到原始字符串比较
    best_raw = max(matched, key=lambda x: x[1] or x[0])[0]
    return best_raw


def is_today(publish_time_str: str | None, today_date: date | None = None) -> bool:
    """判断是否为当天日期"""
    if not publish_time_str:
        return False
    if today_date is None:
        today_date = date.today()
    # 提取日期部分：找到前10个字符（YYYY-MM-DD）
    date_part = publish_time_str[:10]
    try:
        pub_date = datetime.strptime(date_part, "%Y-%m-%d").date()
        return pub_date == today_date
    except (ValueError, TypeError):
        return False


# ---------------------------------------------------------------------------
# 策略0：URL 路径日期提取（最低优先兜底）
# ---------------------------------------------------------------------------

def extract_date_from_url(url: str) -> str | None:
    """
    从 URL 路径中提取日期。

    支持格式：
      - 人民网: .../n1/YYYY/MMDD/...  →  YYYY-MM-DD 00:00:00
      - 通用:   .../YYYY/MMDD/...    →  YYYY-MM-DD 00:00:00
    """
    if not url:
        return None

    # 人民网: /n1/2026/0528/c1001-xxx.html
    m = re.search(r'/n1/(\d{4})/(\d{4})/', url)
    if m:
        year, md = m.group(1), m.group(2)
        try:
            month, day = int(md[:2]), int(md[2:])
            if 1 <= month <= 12 and 1 <= day <= 31:
                return f"{year}-{month:02d}-{day:02d} 00:00:00"
        except ValueError:
            pass

    # 通用: /YYYY/MMDD/ 或 /YYYY/MMDD.
    m = re.search(r'/(\d{4})/(\d{4})(?:/|\.|\?)', url)
    if m:
        year, md = m.group(1), m.group(2)
        try:
            month, day = int(md[:2]), int(md[2:])
            if 1 <= month <= 12 and 1 <= day <= 31:
                return f"{year}-{month:02d}-{day:02d} 00:00:00"
        except ValueError:
            pass

    return None


# ---------------------------------------------------------------------------
# 策略1：HTML meta og:published_time / time[datetime]（标准元数据，最优先特殊解析）
# ---------------------------------------------------------------------------

def _extract_meta_datetime(html: str) -> str | None:
    """从 meta og:published_time 或 <time datetime=""> 提取标准 ISO 日期"""
    # og:published_time（两种 attribute 顺序）
    m = re.search(
        r'<meta[^>]+(?:property|name)=["\']og:published_time["\'][^>]+content=["\']([^"\']+)["\']',
        html, re.IGNORECASE
    )
    if not m:
        m = re.search(
            r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|name)=["\']og:published_time["\']',
            html, re.IGNORECASE
        )
    if m:
        t = parse_publish_time(m.group(1))
        if t:
            return t

    # <time datetime="...">
    m = re.search(r'<time[^>]+datetime=["\']([^"\']+)["\']', html, re.IGNORECASE)
    if m:
        t = parse_publish_time(m.group(1))
        if t:
            return t

    return None


# ---------------------------------------------------------------------------
# 策略2：HTML 结构化日期块（次优先，正则失败后用）
# ---------------------------------------------------------------------------

def _extract_html_structured(html: str) -> str | None:
    """从特定网站的 HTML 结构中提取日期（次优先，在正则失败后用）"""
    # news_bt1_left
    m = re.search(r'<div\s+class="news_bt1_left"[^>]*>([\s\S]*?)</div>', html)
    if m:
        t = parse_publish_time(m.group(1))
        if t:
            return t

    # id="newstime"（人民网）
    m = re.search(r'<b\s+id="newstime"[^>]*>([\s\S]*?)</b>', html)
    if m:
        t = parse_publish_time(m.group(1))
        if t:
            return t

    # w-createtime-date + time 分离式（csia 等）
    m = re.search(
        r'class="[^"]*w-createtime-date[^"]*"[^>]*>\s*([\d-]+)\s*</span>\s*'
        r'<[^>]*class="[^"]*w-createtime-time[^"]*"[^>]*>\s*([\d:]+)\s*</span>',
        html
    )
    if m:
        combined = f"{m.group(1).strip()} {m.group(2).strip()}"
        t = parse_publish_time(combined)
        if t:
            return t

    # detail_left（SMM 等）
    m = re.search(r'class="[^"]*detail_left[^"]*"[^>]*>([\s\S]*?)</div>', html)
    if m:
        text = re.sub(r'<[^>]+>', '', m.group(1)).strip()
        t = parse_publish_time(text)
        if t:
            return t

    # news_info
    m = re.search(r'<div\s+class="news_info"[^>]*>([\s\S]*?)</div>', html)
    if m:
        t = parse_publish_time(m.group(1))
        if t:
            return t

    # meta datePublished / dateModified / publishdate
    m = re.search(
        r'(?:datePublished|dateModified|pubdate|publishdate)[^>]*content="([^"]+)"',
        html, re.IGNORECASE
    )
    if m:
        t = parse_publish_time(m.group(1))
        if t:
            return t

    return None


# ---------------------------------------------------------------------------
# 主入口：extract_date_from_html
# 优先级：① COMBINED_DATE_REGEX 全文本扫描（无截断）→ ② 结构化 HTML 解析 → ③ URL 路径兜底
# ---------------------------------------------------------------------------

def extract_date_from_html(html: str, url: str = "") -> str | None:
    """
    从 HTML 中提取日期时间。

    优先级：
      1. COMBINED_DATE_REGEX 全文本扫描（无截断）
      2. 结构化 HTML 解析（og:meta / time[datetime] / site-specific）
      3. URL 路径兜底（最低优先）
    """
    if not html:
        return None

    # 策略1：全文正则扫描（最通用，无截断限制）
    t = parse_publish_time(html)
    if t:
        return t

    # 策略2：HTML 结构化解析
    t = _extract_meta_datetime(html)
    if t:
        return t

    t = _extract_html_structured(html)
    if t:
        return t

    # 策略3：URL 路径兜底
    if url:
        t = extract_date_from_url(url)
        if t:
            return t

    return None


def check_article_quality(title: str, content: str, publish_time: str | None) -> dict:
    """检查文章内容质量，返回报告字典"""
    report = {
        "passed": True,
        "issues": [],
        "content_length": len(content),
        "title_length": len(title),
        "has_time": publish_time is not None,
        "time_is_zero": False,
    }

    if len(content) < 200:
        report["passed"] = False
        report["issues"].append(f"content_too_short:{len(content)}")

    if not title or len(title) < 5:
        report["passed"] = False
        report["issues"].append("title_missing_or_too_short")

    if publish_time:
        time_part = publish_time.split(" ")[1] if " " in publish_time else ""
        if time_part == "00:00:00":
            report["time_is_zero"] = True
            report["issues"].append("time_may_be_missing")

    noise_patterns = [
        r'^[\[【]?(组图|图集|专辑|专题|专栏|视频|图片|海报)[】\]]',
        r'^!\[.*?\]\(',
        r'^[|\-=]{3,}',
        r'^\d+$',
    ]
    for pat in noise_patterns:
        if re.match(pat, title.strip()):
            report["passed"] = False
            report["issues"].append(f"noise_title:{pat}")
            break

    label_chars = content.count('<') + content.count('>') + content.count('{')
    if label_chars > len(content) * 0.05:
        report["passed"] = False
        report["issues"].append(f"content_impure:label_chars={label_chars}")

    return report


if __name__ == "__main__":
    test_cases = [
        # ISO格式
        ("2026-05-27T06:13:00", "2026-05-27T06:13:00"),
        ("2026-05-27T06:13:00.123", "2026-05-27T06:13:00.123"),
        ("2026-05-27", "2026-05-27"),
        ("2026/05/27", "2026/05/27"),
        ("2026.05.27", "2026.05.27"),
        ("2026-05-27 06:13", "2026-05-27 06:13"),
        ("2026-05-27 06:13:45", "2026-05-27 06:13:45"),
        ("2026/05/27 06:13", "2026/05/27 06:13"),
        ("2026.05.27 06:13:45", "2026.05.27 06:13:45"),
        ("2026年05月27日", "2026年05月27日"),
        ("2026年05月27日06:13", "2026年05月27日06:13"),
        ("2026年05月27日 06:13", "2026年05月27日 06:13"),
        ("2026年05月27日06:13:45", "2026年05月27日06:13:45"),
        ("2026年05月27日 06:13:45", "2026年05月27日 06:13:45"),
        ("2026年05月27日 6:13", "2026年05月27日 6:13"),
        ("Jan 15, 2026", "Jan 15, 2026"),
        ("05/27/2026", "05/27/2026"),
        # JS milliseconds（关键测试：原生存储，不截断毫秒）
        ("2026-05-28 09:15:59.593", "2026-05-28 09:15:59.593"),
        ("new Date('2026-05-28 09:15:59.593')", "2026-05-28 09:15:59.593"),
        # 快科技 JS 真实格式
        ("var g_PostDateStr = new Date('2026-05-27 12:00:04.890');", "2026-05-27 12:00:04.890"),
        # 多日期取最晚（而不是第一个）
        ("2026-05-28T06:07:00 but also 2026-05-27T12:00:04.890", "2026-05-28T06:07:00"),
        ("", None),
        ("foobar", None),
    ]

    print("=" * 60)
    print("parse_publish_time 单元测试（无 strptime，原始格式存储）")
    print("=" * 60)
    passed = failed = 0
    for i, (inp, expected) in enumerate(test_cases):
        result = parse_publish_time(inp)
        ok = result == expected
        print(f"[{'PASS' if ok else 'FAIL'}] #{i+1:02d}  {inp!r:50s} -> {result}  (expected: {expected})")
        passed += ok
        failed += not ok

    print()
    print(f"结果: {passed} 通过, {failed} 失败")
    print()
    print("=" * 60)
    print("extract_date_from_url 单元测试")
    print("=" * 60)
    url_tests = [
        ("http://politics.people.com.cn/n1/2026/0528/c1001-40728816.html", "2026-05-28 00:00:00"),
        ("https://cnenergynews.cn/article/2026/0528/1234567.html", "2026-05-28 00:00:00"),
    ]
    for url, expected in url_tests:
        result = extract_date_from_url(url)
        ok = result == expected
        print(f"[{'PASS' if ok else 'FAIL'}] {url}")
        print(f"       -> {result}  (expected: {expected})")
