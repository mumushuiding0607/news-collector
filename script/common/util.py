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
# 策略2：HTML 结构化日期块（优先于全文正则，避免抓取到页面其他无关日期）
# ---------------------------------------------------------------------------

def _extract_html_structured(html: str) -> str | None:
    """从特定网站的 HTML 结构中提取日期"""
    # ===== 优先：提取 article/source/time 结构（最准确）=====
    # cnenergynews: <span class="time">2026年05月27日 23:22</span>
    m = re.search(r'<span[^>]+class=["\']time["\'][^>]*>\s*(\d{4}[年]\d{1,2}[月]\d{1,2}[日]\s*\d{1,2}:\d{2})', html)
    if m:
        t = parse_publish_time(m.group(1))
        if t:
            return t

    # ===== 通用：article/section 内的日期区域 =====

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

    # ===== meta datePublished / dateModified =====
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
# 辅助：加载 publishTimeExtract 配置
# ---------------------------------------------------------------------------

def get_publish_time_extract(source_name: str) -> dict | None:
    """加载指定数据源的 publishTimeExtract 配置"""
    import json as _json
    from pathlib import Path as _Path
    sources_path = _Path(__file__).parent.parent.parent / "config" / "sources.json"
    if not sources_path.exists():
        return None
    try:
        data = _json.loads(sources_path.read_text(encoding="utf-8"))
        for source in data.get("sources", []):
            if source.get("name") == source_name:
                return source.get("publishTimeExtract")
        return None
    except Exception:
        return None


# ---------------------------------------------------------------------------
# 策略：使用 source-specific 的 publishTimeExtract
# ---------------------------------------------------------------------------

def extract_date_by_pattern(html: str, publish_time_extract: dict | None) -> str | None:
    """使用 source-specific 的 publishTimeExtract 提取日期"""
    if not html or not publish_time_extract:
        return None
    import re as _re

    # 策略1：主正则
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

    # 策略2：fallbackPattern
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


# ---------------------------------------------------------------------------
# 主入口：extract_date_from_html
# 优先级：① source-specific publishTimeExtract → ② 结构化 HTML 解析 → ③ COMBINED_DATE_REGEX 扫描 → ④ URL 路径兜底
# ---------------------------------------------------------------------------

def extract_date_from_html(html: str, url: str = "", source_name: str = "") -> str | None:
    """
    从 HTML 中提取日期时间。

    优先级：
      1. source-specific publishTimeExtract（当提供 source_name 时）
      2. HTML 结构化解析（og:meta / article结构内日期 / site-specific）
      3. COMBINED_DATE_REGEX 全文本扫描（无截断）
      4. URL 路径兜底（最低优先）
    """
    if not html:
        return None

    # 策略0：source-specific publishTimeExtract（优先）
    if source_name:
        pte = get_publish_time_extract(source_name)
        if pte:
            t = extract_date_by_pattern(html, pte)
            if t:
                return t

    # 策略1：HTML 结构化解析
    t = _extract_html_structured(html)
    if t:
        return t

    t = _extract_meta_datetime(html)
    if t:
        return t

    # 策略2：全文正则扫描（兜底）
    t = parse_publish_time(html)
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


# ---------------------------------------------------------------------------
# 内容提取：从原始 HTML 中提取干净的文章正文
# ---------------------------------------------------------------------------

# 内容区域的 HTML 提取模式（按优先级排序）
CONTENT_EXTRACT_PATTERNS = [
    # 1. mydrivers.com: AI摘要（最干净）
    (r'AI摘要[^>]*内容由AI生成[^>]*"([^"]{20,})"', re.DOTALL),
    # 2. mydrivers.com: 正文（从"快科技X月X日消息"到"【本文结束】"）
    (r'(快科技\d{1,2}月\d{1,2}日[^科][^计][^详][^细][^文][^件][^管][^热][^好][^问][^相][^删].*?【本文结束】)', re.DOTALL),
    # 3. 通用: <article>标签
    (r'<article[^>]*>(.*?)</article>', re.DOTALL),
    # 4. 通用: class="article-content" / id="article-content"
    (r'(?:class|id)=["\'][^"\']*(?:article|content|post|entry)[^"\']*["\'][^>]*>(.*?)(?:</div>|</article>)', re.DOTALL),
    # 5. 通用: <div class="content">...</div>
    (r'<div[^>]+class=["\'][^"\']*content[^"\']*["\'][^>]*>([\s\S]{200,})</div>', re.DOTALL),
]


def extract_content_from_html(html: str, url: str = "") -> dict:
    """
    从原始 HTML 中提取文章正文内容。

    返回:
        {
            "content": str,       # 干净的文章正文
            "ai_summary": str,    # AI摘要（如有）
            "source": str,        # 来源网站标识
            "raw_length": int,    # 原始内容长度
        }
    """
    import html as html_module

    result = {
        "content": "",
        "ai_summary": "",
        "source": _detect_source(url, html),
        "raw_length": len(html),
    }

    if not html or not html.strip():
        return result

    # -------- 1. 提取 AI 摘要 --------
    ai_summary_match = re.search(r'AI摘要[^>]*内容由AI生成[^>]*"([^"]{20,})"', html)
    if not ai_summary_match:
        ai_summary_match = re.search(r'"AI摘要"[^>]*>([^<]{50,})', html)
    if ai_summary_match:
        result["ai_summary"] = ai_summary_match.group(1).strip()

    # -------- 2. 提取正文内容 --------
    content = ""

    # mydrivers.com 特殊处理：跳过 AI摘要pattern，直接用正文pattern
    if result["source"] == "mydrivers":
        patterns_to_try = CONTENT_EXTRACT_PATTERNS[1:]  # skip AI summary
    else:
        patterns_to_try = CONTENT_EXTRACT_PATTERNS

    for pattern, flags in patterns_to_try:
        m = re.search(pattern, html, flags)
        if m:
            candidate = m.group(1) if m.lastindex else m.group(0)
            # 去除 HTML 标签
            text = re.sub(r'<[^>]+>', '', candidate)
            text = html_module.unescape(text)
            text = re.sub(r'\s+', ' ', text).strip()
            if len(text) >= 200:
                content = text
                break

    # -------- 3. 如果没提取到，尝试分段提取 --------
    if not content:
        content = _extract_content_fallback(html)

    # -------- 4. 清理残留内容 --------
    # 去除图片、链接标记等 markdown 噪音
    if content:
        content = re.sub(r'!\[([^\]]*)\]\([^)]+\)', '', content)
        content = re.sub(r'\[\]\([^)]+\)', '', content)
        content = re.sub(r'#{1,6}\s+', '', content)
        content = re.sub(r'\s+', ' ', content).strip()
        content = content.rstrip('【本文结束】').rstrip()

    result["content"] = content
    return result


def _detect_source(url: str = "", html: str = "") -> str:
    """
    检测文章来源，优先从 HTML 内容判断，URL 作为兜底

    HTML 特征：
      - cnenergynews: 有 class="article_content" / class="w-createtime"
      - mydrivers: 有 class="news_detail" / id="news_detail"
      - smm: 有 class="live_detail" / news.smm.cn
      - people: 有 class="people_news_content"
    """
    # 1. 从 HTML 内容检测（更可靠）
    if html:
        if "cnenergynews.cn" in html or 'class="article_content"' in html or 'class="w-createtime"' in html:
            return "cnenergynews"
        if 'id="news_detail"' in html or 'class="news_detail"' in html:
            return "mydrivers"
        if 'class="live_detail"' in html or "news.smm.cn" in html:
            return "smm"
        if 'class="people_news_content"' in html:
            return "people"
        if 'class="article"' in html and 'pubdate' in html:
            return "cnenergynews"

    # 2. 从 URL 检测（兜底）
    if url:
        if "mydrivers.com" in url:
            return "mydrivers"
        elif "cnenergynews.cn" in url:
            return "cnenergynews"
        elif "smm.cn" in url:
            return "smm"
        elif "people.com.cn" in url:
            return "people"
        elif "moa.gov.cn" in url:
            return "moa"

    return "unknown"


def _extract_content_fallback(html: str) -> str:
    """
    从 HTML 中提取正文内容的兜底方法。

    策略：
      1. 先找文章核心区域（article_content / rtext / detail_left）
      2. 只从核心区域内提取 <p> 标签
      3. 过滤掉来源/时间/编辑/版权等 Boilerplate 行
    """
    import html as html_module

    # -------- 1. 找文章核心区域 --------
    article_area = ""

    # cnenergynews: <section data-type="rtext">
    m = re.search(r'<section[^>]+data-type=["\']rtext["\'][^>]*>(.*?)</section>', html, re.DOTALL)
    if m:
        article_area = m.group(1)

    # cnenergynews: <div class="article_content">
    if not article_area:
        m = re.search(r'<div[^>]+class=["\'][^"\']*article_content[^"\']*["\'][^>]*>(.*?)</div>', html, re.DOTALL)
        if m:
            article_area = m.group(1)

    # cnenergynews: detail_left
    if not article_area:
        m = re.search(r'<div[^>]+class=["\'][^"\']*detail_left[^"\']*["\'][^>]*>(.*?)</div>', html, re.DOTALL)
        if m:
            article_area = m.group(1)

    # 通用: article 标签
    if not article_area:
        m = re.search(r'<article[^>]*>(.*?)</article>', html, re.DOTALL)
        if m:
            article_area = m.group(1)

    # -------- 2. 从核心区域提取段落 --------
    if article_area:
        paragraphs = re.findall(r'<p[^>]*>(.*?)</p>', article_area, re.DOTALL | re.IGNORECASE)
        text_blocks = []
        for p in paragraphs:
            text = re.sub(r'<[^>]+>', '', p)
            text = html_module.unescape(text).strip()
            if len(text) >= 15:
                # 过滤 Boilerplate 行
                if _is_boilerplate_paragraph(text):
                    continue
                text_blocks.append(text)
        if text_blocks:
            return ' '.join(text_blocks)

    # -------- 3. 全局 <p> 标签（带 Boilerplate 过滤）--------
    paragraphs = re.findall(r'<p[^>]*>(.*?)</p>', html, re.DOTALL | re.IGNORECASE)
    text_blocks = []
    for p in paragraphs:
        text = re.sub(r'<[^>]+>', '', p)
        text = html_module.unescape(text).strip()
        if len(text) >= 15 and not _is_boilerplate_paragraph(text):
            text_blocks.append(text)

    if text_blocks:
        return ' '.join(text_blocks)

    # -------- 4. 最后兜底：所有文本 --------
    text = re.sub(r'<[^>]+>', ' ', html)
    text = html_module.unescape(text)
    text = re.sub(r'\s{3,}', ' ', text).strip()
    return text


def _is_boilerplate_paragraph(text: str) -> bool:
    """判断段落是否为 Boilerplate（噪音内容）"""
    # 移除空白后的文本
    t = text.strip()
    if not t:
        return True

    # 关键词过滤
    bp_keywords = [
        '文章来源', '来源：', '来源:', '责任编辑', '编辑：', '作者：',
        '未经授权', '严禁转载', '版权声明', '投稿：', '投稿热线',
        '微信：', '邮箱：', 'qq.com', '新浪微博', '官方微博',
        '扫描二维码', '长按识别', '关注我们', '合作伙伴',
        '相关资讯', '热门文章', '精彩推荐', '相关阅读',
        '天眼查App显示', '数据显示', '据.*?消息', '年.*?月.*?日',
        '免责声明', '违法和不良信息', '举报中心',
    ]
    for kw in bp_keywords:
        if kw in t:
            return True

    # 纯链接类（大量URL或[]()格式）
    if re.match(r'^\[.+\]\(https?://', t) or t.startswith('http'):
        return True

    # 太短的日期行
    if re.match(r'^\d{4}[-/年]\d{1,2}[-/月]\d{1,2}[日]?\s*\d{1,2}:\d{2}', t) and len(t) < 30:
        return True

    # 合作伙伴列表行
    if any(org in t for org in ['国家发改委', '国资委', '国家能源局', '中国华能', '中国电建']):
        if len(t) < 50:
            return True

    return False


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
