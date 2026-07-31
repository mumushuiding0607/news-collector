"""
datetimeutil.py - 日期时间解析工具

从文本/HTML/URL 中提取规范化日期。
提供统一的时间格式化辅助函数。
"""

import re
from datetime import datetime, date


# =============================================================================
# 时间格式化辅助函数
# =============================================================================

def now_iso() -> str:
    """返回当前时间，格式：YYYY-MM-DD HH:MM:SS"""
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def today_iso() -> str:
    """返回当前日期，格式：YYYY-MM-DD"""
    return date.today().strftime('%Y-%m-%d')


# ==================== 通用日期格式化（按 format name）====================

# 支持的日期格式名（与 script.discovery.util.analyze_api 保持一致）
SUPPORTED_DATE_FORMATS = ('YYYYMMDD', 'YYYY-MM-DD', 'YYYY/MM/DD', 'TIMESTAMP_S', 'TIMESTAMP_MS')


def format_date_by_format(d: date, fmt: str) -> str:
    """按 fmt 格式化日期。支持 5 种格式：
        - YYYYMMDD / YYYY-MM-DD / YYYY/MM/DD：字符串日期
        - TIMESTAMP_S / TIMESTAMP_MS：Unix 时间戳（秒/毫秒）
    """
    if fmt == 'YYYYMMDD':
        return d.strftime('%Y%m%d')
    if fmt == 'YYYY-MM-DD':
        return d.strftime('%Y-%m-%d')
    if fmt == 'YYYY/MM/DD':
        return d.strftime('%Y/%m/%d')
    if fmt == 'TIMESTAMP_S':
        return str(int(datetime(d.year, d.month, d.day).timestamp()))
    if fmt == 'TIMESTAMP_MS':
        return str(int(datetime(d.year, d.month, d.day).timestamp() * 1000))
    raise ValueError(f"unsupported date format: {fmt}")


def is_separator_date_format(fmt: str) -> bool:
    """日期格式是否带分隔符（YYYY-MM-DD / YYYY/MM/DD），可用于 startswith 比较。
    YYYYMMDD / TIMESTAMP_* 无分隔符，比较时需用 ==。
    """
    return fmt in ('YYYY-MM-DD', 'YYYY/MM/DD')


# ==================== 统一日期时间正则模式 ====================
# 所有 script 目录下的模块必须引用此处定义的模式，禁止自行定义重复的正则

DATETIME_PATTERNS = [
    r'\d{4}年\d{1,2}月\d{1,2}日',                           # 2026年06月11日
    r'\d{4}-\d{1,2}-\d{1,2}',                               # 2026-06-11
    r'\d{4}/\d{1,2}/\d{1,2}',                               # 2026/06/11
    r'\d{4}年\d{1,2}月\d{1,2}日\s+\d{1,2}:\d{2}',            # 2026年06月11日 12:02
    r'\d{4}-\d{1,2}-\d{1,2}\s+\d{1,2}:\d{2}',              # 2026-06-11 12:02
    r'\d{4}-\d{1,2}-\d{1,2}\s+\d{1,2}:\d{2}:\d{2}',         # 2026-06-11 12:02:36
    r'\d{4}/\d{1,2}/\d{1,2}\s+\d{1,2}:\d{2}',              # 2026/06/11 12:02
    r'\d{1,2}月\d{1,2}日',                                   # 06月11日
    r'\d{1,2}:\d{2}',                                       # 12:02
    r'(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}',  # July 28, 2026
    r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},?\s+\d{4}',  # Jan 3, 2026 / Mar 3, 2026
]

DATETIME_REGEX = re.compile('|'.join(DATETIME_PATTERNS), re.IGNORECASE)

# 用于标题尾部日期清理（去除尾部日期后缀）
DATE_TRAILING_REGEX = re.compile(r'\s*\d{4}[-/.]\d{1,2}[-/.]\d{1,2}\s*$')

# ==================== 完整提取正则（用于 parse_publish_time） ====================

COMBINED_DATE_REGEX = re.compile(
    r'(?P<iso>(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})T(\d{1,2}):(\d{2}):(\d{2})(?:\.\d+)?)'
    r'|(?P<num>(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})(?:\s+(\d{1,2}):(\d{2})(?::(\d{2}))?(?:\.\d+)?)?)'
    r'|(?P<cn>(\d{4})年(\d{1,2})月(\d{1,2})日(?:\s*(\d{1,2}):(\d{2})(?::(\d{2}))?(?:\.\d+)?)?)'
    r'|(?P<en_full>(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4})'
    r'|(?P<en>(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},?\s+\d{4})'
    r'|(?P<us>(\d{1,2})/(\d{1,2})/(\d{4}))'
)


def _normalize_to_iso(date_str: str) -> str | None:
    """将任意格式日期字符串规范化为 YYYY-MM-DD HH:MM:SS"""
    s = date_str.strip()
    if re.match(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', s):
        return s
    if re.match(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}', s):
        return s[:10] + ' ' + s[11:19]
    if re.match(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$', s):
        return s[:10] + ' 00:00:00'
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
    # 无年份的月-日 时:分（兜底用当前年份）
    m = re.match(r'(\d{1,2})[-/](\d{1,2})(?:\s+(\d{1,2}):(\d{2})(?::(\d{2}))?)?', s)
    if m:
        mo, d = m.group(1), m.group(2)
        h = m.group(3) or '00'
        mi = m.group(4) or '00'
        sec = m.group(5) or '00'
        try:
            y = date.today().year
            return f"{y}-{int(mo):02d}-{int(d):02d} {int(h):02d}:{int(mi):02d}:{int(sec):02d}"
        except ValueError:
            pass
    # 英文月份格式：July 28, 2026 或 Jan 3, 2026
    m = re.match(r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(\d{4})', s, re.IGNORECASE)
    if m:
        month_name, d, y = m.group(1), m.group(2), m.group(3)
        try:
            mo = {'january': 1, 'february': 2, 'march': 3, 'april': 4, 'may': 5, 'june': 6,
                  'july': 7, 'august': 8, 'september': 9, 'october': 10, 'november': 11, 'december': 12}[month_name.lower()]
            return f"{y}-{int(mo):02d}-{int(d):02d} 00:00:00"
        except (ValueError, KeyError):
            pass
    m = re.match(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{1,2}),?\s+(\d{4})', s, re.IGNORECASE)
    if m:
        month_abbr, d, y = m.group(1), m.group(2), m.group(3)
        try:
            mo = {'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
                  'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12}[month_abbr.lower()]
            return f"{y}-{int(mo):02d}-{int(d):02d} 00:00:00"
        except (ValueError, KeyError):
            pass
    return None


def parse_publish_time(text: str) -> str | None:
    """从文本中提取日期时间，返回统一格式 YYYY-MM-DD HH:MM:SS"""
    if not text:
        return None
    matched = []
    for m in COMBINED_DATE_REGEX.finditer(text):
        raw = m.group().strip()
        iso = _normalize_to_iso(raw)
        if iso:
            matched.append(iso)
    if not matched:
        # 兜底：COMBINED_DATE_REGEX 全部要求 4 位数年，对无年份的 MM-DD HH:MM 不命中。
        # 这里直接对 text 整体跑一次 _normalize_to_iso（它支持无年份 + 当前年份兜底）。
        iso = _normalize_to_iso(text.strip())
        if iso:
            matched.append(iso)
    if not matched:
        return None
    # 返回最完整的（包含最多时间信息的）格式
    return max(matched, key=lambda x: len(x))


def extract_time_text_from_element(time_el) -> str:
    """从 time_selector 命中的元素中提取时间文本。

    支持 w-createtime-date + w-createtime-time 分拆模式（中间无空格会被 get_text 拼接丢失时间）。
    """
    import re as _re
    date_span = time_el.find('span', class_=_re.compile(r'w-createtime-date'))
    if date_span:
        text = date_span.get_text(strip=True)
        time_span = date_span.find_next_sibling('span', class_=_re.compile(r'w-createtime-time'))
        if time_span:
            text += ' ' + time_span.get_text(strip=True)
        return text
    return time_el.get_text(strip=True)


def is_today(publish_time_str: str | None, today_date: date | None = None) -> bool:
    """判断是否为当天日期"""
    if not publish_time_str:
        return False
    if today_date is None:
        today_date = date.today()
    normalized = _normalize_to_iso(publish_time_str)
    if normalized:
        date_part = normalized[:10]
    else:
        date_part = publish_time_str[:10]
    try:
        pub_date = datetime.strptime(date_part, "%Y-%m-%d").date()
        return pub_date == today_date
    except (ValueError, TypeError):
        return False


def extract_date_from_url(url: str) -> str | None:
    """从 URL 路径中提取日期"""
    if not url:
        return None
    # 人民网: /n1/YYYY/MMDD/
    m = re.search(r'/n1/(\d{4})/(\d{4})/', url)
    if m:
        year, md = m.group(1), m.group(2)
        try:
            month, day = int(md[:2]), int(md[2:])
            if 1 <= month <= 12 and 1 <= day <= 31:
                return f"{year}-{month:02d}-{day:02d} 00:00:00"
        except ValueError:
            pass
    # 通用: /YYYY/MMDD/
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


def _extract_meta_datetime(html: str) -> str | None:
    """从 meta og:published_time 或 <time datetime=""> 提取标准 ISO 日期"""
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
    m = re.search(r'<time[^>]+datetime=["\']([^"\']+)["\']', html, re.IGNORECASE)
    if m:
        t = parse_publish_time(m.group(1))
        if t:
            return t
    return None


def _extract_html_structured(html: str) -> str | None:
    """从 HTML 结构中提取日期"""
    m = re.search(r'<span[^>]+class=["\']time["\'][^>]*>\s*(\d{4}[年]\d{1,2}[月]\d{1,2}[日]\s*\d{1,2}:\d{2})', html)
    if m:
        t = parse_publish_time(m.group(1))
        if t:
            return t
    m = re.search(r'<div\s+class="news_bt1_left"[^>]*>([\s\S]*?)</div>', html)
    if m:
        t = parse_publish_time(m.group(1))
        if t:
            return t
    m = re.search(r'<b\s+id="newstime"[^>]*>([\s\S]*?)</b>', html)
    if m:
        t = parse_publish_time(m.group(1))
        if t:
            return t
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
    m = re.search(r'class="[^"]*detail_left[^"]*"[^>]*>([\s\S]*?)</div>', html)
    if m:
        text = re.sub(r'<[^>]+>', '', m.group(1)).strip()
        t = parse_publish_time(text)
        if t:
            return t
    m = re.search(r'<div\s+class="news_info"[^>]*>([\s\S]*?)</div>', html)
    if m:
        t = parse_publish_time(m.group(1))
        if t:
            return t
    m = re.search(
        r'(?:datePublished|dateModified|pubdate|publishdate)[^>]*content="([^"]+)"',
        html, re.IGNORECASE
    )
    if m:
        t = parse_publish_time(m.group(1))
        if t:
            return t
    return None


def get_publish_time_extract(source_name: str) -> dict | None:
    """加载指定数据源的 publishTimeExtract 配置（优先从 source_crawl_configs，兜底 sources.json）"""
    try:
        from script.db.sources_db import get_publish_time_extract_by_name
        pattern = get_publish_time_extract_by_name(source_name)
        if pattern:
            return {"pattern": pattern}
    except Exception:
        pass
    # 兜底 sources.json
    import json as _json
    from pathlib import Path as _Path
    sources_path = _Path(__file__).parent.parent.parent / "config" / "sources.json"
    if not sources_path.exists():
        return None
    try:
        data = _json.loads(sources_path.read_text(encoding="utf-8"))
        for source in data.get("sources", []):
            if source.get("name") == source_name:
                pte = source.get("publishTimeExtract")
                if pte:
                    return pte
        return None
    except Exception:
        return None


def extract_date_by_pattern(html: str, publish_time_extract: dict | None) -> str | None:
    """使用 source-specific 的 publishTimeExtract 提取日期"""
    if not html or not publish_time_extract:
        return None
    import re as _re
    pattern = publish_time_extract.get("pattern", "")
    if pattern:
        try:
            m = _re.search(pattern, html, _re.DOTALL | _re.IGNORECASE)
            if m:
                try:
                    g1 = m.group(1)
                    date_str = g1.strip() if g1 else m.group(0).strip()
                except (IndexError, AttributeError):
                    date_str = m.group(0).strip() if m.group(0) else None
                if date_str:
                    t = parse_publish_time(date_str)
                    if t:
                        return t
        except _re.error:
            pass
    fallback = publish_time_extract.get("fallbackPattern", "")
    if fallback:
        try:
            m = _re.search(fallback, html, _re.DOTALL | _re.IGNORECASE)
            if m:
                try:
                    g1 = m.group(1)
                    date_str = g1.strip() if g1 else m.group(0).strip()
                except (IndexError, AttributeError):
                    date_str = m.group(0).strip() if m.group(0) else None
                if date_str:
                    t = parse_publish_time(date_str)
                    if t:
                        return t
        except _re.error:
            pass
    return None


def extract_date_from_html(html: str, url: str = "", source_name: str = "") -> str | None:
    """从 HTML 中提取日期时间（优先级：source-specific > 结构化HTML > 全文正则 > URL兜底）"""
    if not html:
        return None
    if source_name:
        pte = get_publish_time_extract(source_name)
        if pte:
            t = extract_date_by_pattern(html, pte)
            if t:
                return t
    t = _extract_html_structured(html)
    if t:
        return t
    t = _extract_meta_datetime(html)
    if t:
        return t
    t = parse_publish_time(html)
    if t:
        return t
    if url:
        t = extract_date_from_url(url)
        if t:
            return t
    return None


if __name__ == "__main__":
    test_cases = [
        ("2026-05-27T06:13:00", "2026-05-27T06:13:00"),
        ("2026-05-27T06:13:00.123", "2026-05-27T06:13:00.123"),
        ("2026-05-27", "2026-05-27"),
        ("2026/05/27", "2026/05/27"),
        ("2026.05.27", "2026.05.27"),
        ("2026-05-27 06:13", "2026-05-27 06:13"),
        ("2026-05-27 06:13:45", "2026-05-27 06:13:45"),
        ("2026年05月27日", "2026年05月27日"),
        ("2026年05月27日06:13", "2026年05月27日06:13"),
        ("Jan 15, 2026", "Jan 15, 2026"),
        ("05/27/2026", "05/27/2026"),
        ("2026-05-28 09:15:59.593", "2026-05-28 09:15:59.593"),
        ("", None),
        ("foobar", None),
    ]
    print("=" * 60)
    print("parse_publish_time 单元测试")
    print("=" * 60)
    passed = failed = 0
    for i, (inp, expected) in enumerate(test_cases):
        result = parse_publish_time(inp)
        ok = result == expected
        print(f"[{'PASS' if ok else 'FAIL'}] #{i+1:02d}  {inp!r:50s} -> {result}  (expected: {expected})")
        passed += ok
        failed += not ok
    print(f"\n结果: {passed} 通过, {failed} 失败")