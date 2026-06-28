"""
source_finder.py - 从异动消息中发现数据源

使用正则表达式从异动消息标题中提取数据源名称
"""
import re
from dataclasses import dataclass
from urllib.parse import urljoin

from script.log import log as _log, init_log


def log(msg: str):
    _log("source_discovery", msg)


@dataclass
class AnomalyInfo:
    """异动信息"""
    title: str = ""          # 异动标题
    url: str = ""            # 文章链接
    time: str = ""           # 发布时间
    source_name: str = ""    # 数据源名称


def parse_anomaly_list_html(html: str, base_url: str = "") -> list[AnomalyInfo]:
    """解析异动消息列表 HTML"""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, 'html.parser')
    anomalies = []

    for item in soup.find_all('a', class_='news-link'):
        info = AnomalyInfo()
        info.url = item.get('href', '')
        if info.url and not info.url.startswith(('http://', 'https://')):
            info.url = urljoin(base_url, info.url)
        info.title = item.get('title', '') or item.get_text(strip=True)

        time_match = re.search(r'/(\d{8})/', info.url)
        if time_match:
            t = time_match.group(1)
            info.time = f"{t[:4]}-{t[4:6]}-{t[6:8]}"

        if info.title and info.url:
            anomalies.append(info)

    return anomalies


# 来源标注正则：据XXXX报道、据XXXX讯、来源：XXXX、XXXX6月11日电 等
_SOURCE_ANNOTATION_RE = re.compile(
    r'来源：([\u4e00-\u9fa5]+)|据([\u4e00-\u9fa5]*(?:社|报|网|台|讯|闻|经|济|日|晚|周|月))(?:\d{1,2}月\d{1,2}日|\d{4}年\d{1,2}月\d{1,2}日)?(?:报道|讯|电)|据([\u4e00-\u9fa5]*(?:社|报|网|台|讯|闻|经|济|日|晚|周|月))(?=，)|据([\u4e00-\u9fa5]*(?:社|报|网|台|讯|闻|经|济|日|晚|周|月))$|([\u4e00-\u9fa5]+)\d{1,2}月\d{1,2}日电',
    re.IGNORECASE,
)


def extract_source_name(title: str) -> str:
    """
    从异动标题中提取数据源名称。

    匹配模式：
    - "据XXXX6月11日报道" → XXXX
    - "据XXXX讯" → XXXX
    - "来源：XXXX" → XXXX
    - "XXXX6月11日电" → XXXX
    """
    m = _SOURCE_ANNOTATION_RE.search(title)
    if m:
        return (m.group(1) or m.group(2) or m.group(3) or m.group(4) or m.group(5) or '').strip()
    return ''


def discover_sources(url: str, save_to_db: bool = True) -> dict:
    """从异动消息页面发现数据源"""
    from script.discovery.raw_fetch import fetch_raw_html

    init_log()
    log(f"开始分析: {url}")

    html = fetch_raw_html(url)
    if not html:
        log(f"获取页面失败")
        return {'error': '无法获取页面', 'url': url}

    anomalies = parse_anomaly_list_html(html, url)
    log(f"解析到 {len(anomalies)} 条异动消息，提取数据源...")

    # 正则提取每条异动的数据源
    for i, a in enumerate(anomalies, 1):
        a.source_name = extract_source_name(a.title)
        source_info = f"[{a.source_name}]" if a.source_name else "[无数据源]"
        log(f"  [{i:02d}] {a.title[:35]}... {source_info}")

    # 统计每个数据源的出现次数
    source_map = {}
    for a in anomalies:
        name = a.source_name or '未知'
        if name in source_map:
            source_map[name]['count'] += 1
            source_map[name]['articles'].append(a.title[:30])
        else:
            source_map[name] = {'count': 1, 'articles': [a.title[:30]]}

    # 按次数排序
    sorted_sources = sorted(source_map.items(), key=lambda x: -x[1]['count'])

    log(f"\\n发现数据源 {len(sorted_sources)} 个:")
    for name, info in sorted_sources:
        log(f"  - {name}: {info['count']}次")

    # 保存有数据源的异动消息到数据库
    if save_to_db:
        from script.db.anomaly_news import batch_save_anomaly_news
        anomalies_with_source = [
            {
                'title': a.title,
                'url': a.url,
                'publish_time': a.time,
                'source_name': a.source_name,
            }
            for a in anomalies if a.source_name
        ]
        if anomalies_with_source:
            saved_count = batch_save_anomaly_news(anomalies_with_source)
            log(f"已保存 {saved_count} 条异动消息到数据库")

    return {
        'total_anomalies': len(anomalies),
        'anomalies': [
            {
                'title': a.title,
                'url': a.url,
                'time': a.time,
                'source_name': a.source_name,
            }
            for a in anomalies
        ],
        'discovered_sources': [
            {'name': name, 'count': info['count']}
            for name, info in sorted_sources
        ],
    }


if __name__ == '__main__':
    import sys
    url = sys.argv[1] if len(sys.argv) > 1 else 'https://yuanchuang.10jqka.com.cn/mrnxgg_list/index_2.shtml'

    result = discover_sources(url)
    print()
    print(f"异动消息: {result['total_anomalies']} 条")
    print(f"数据源: {len(result['discovered_sources'])} 个")
    for s in result['discovered_sources']:
        print(f"  {s['name']} ({s['count']}次)")