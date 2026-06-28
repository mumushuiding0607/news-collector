"""
_patterns_b.py - 正则模式常量（高级）
"""

from __future__ import annotations

import re

# =============================================================================
# Boilerplate
# =============================================================================
BOILERPLATE_PATTERNS = [
    (re.compile(p, f), '') for p, f in [
        (r"^(【.*?】\s*)?(转载|摘录|来源|出处|原文链接|原文地址|来源网址).*?$", re.MULTILINE | re.IGNORECASE),
        (r"^责编：.*$", re.MULTILINE),
        (r"^责任编辑：.*$", re.MULTILINE),
        (r"^编辑：.*$", re.MULTILINE),
        (r"^作者：.*$", re.MULTILINE),
        (r"^(如需转载|转载需|转载授权|侵权举报|举报).*?$", re.MULTILINE),
        (r"^[|\-=]{3,}$", re.MULTILINE),
        (r"(?:扫描|长按|识别).*?(?:二维码|关注|公众|微信号).*?$", re.IGNORECASE | re.MULTILINE),
        (r"^©?\s*版权.*?$", re.MULTILINE | re.IGNORECASE),
        (r"^本文结束.*$", re.MULTILINE),
        (r"^【相关.*?】.*$", re.MULTILINE),
        (r"^广告\s*人民日报主管.*?主办\s*网站地图.*?$", re.MULTILINE),
        (r"^网站地图\s*联系我们\s*首页.*?$", re.MULTILINE),
        (r"^人民日报主管.*?有限公司主办\s*$", re.MULTILINE),
        (r"^\d+\.\s*(?:首页|会议会展|正文|新闻|资讯|文章)[^\n]*$", re.MULTILINE),
        (r"^(?:即时新闻|能源要闻|焦点关注|能源评论|能源党建|热点专题|生态环保|人事动态|能源城市|环球视野|产业聚焦|电网电力|新能源|油气)\s*", re.MULTILINE),
        (r"^来源[：:]\s*[^\n]+\d{4}[年-]\d{2}[月-]\d{2}[日]?\s*\d{2}:\d{2}.*$", re.MULTILINE | re.IGNORECASE),
        (r"^热门排行\s*\d[^\n]+$", re.MULTILINE),
        (r"^微信[扫扫]?一扫[^\n]*$", re.MULTILINE),
        (r"^提供新闻线索[^\n]*$", re.MULTILINE),
        (r"^(?:人民智云|人民智作|热门排行|热门推荐|推荐阅读)[^>\n]*$", re.MULTILINE),
        (r"^[^\n]*-->.*$", re.MULTILINE),
        (r"^[^\n]*→.*$", re.MULTILINE),
        (r"^(?:客户端下载|人民日报|人民日报少年|人民网\+|手机人民网|领导留言板|人民视频|人民智云|人民智作)[^\n]*$", re.MULTILINE),
        (r"^关注公众号[^\n]*$", re.MULTILINE),
        (r"^分享让更多人看到[^\n]*$", re.MULTILINE),
        (r"^【.*?】\s*$", re.MULTILINE),
        # 免责声明和风险提示
        (r"^(?:投资有风险|股市有风险|入市需谨慎|风险提示|免责条款|免责声明|Disclaimer).*$", re.MULTILINE | re.IGNORECASE),
        (r"^(?:本文仅供参考|不构成投资建议|据此操作风险自担|市场有风险投资需谨慎).*$", re.MULTILINE | re.IGNORECASE),
        (r"^(?:风险提示：|风险提示 -|免责条款：|免责声明：).*$", re.MULTILINE | re.IGNORECASE),
    ]
]

# =============================================================================
# 正文内容提取
# =============================================================================
CONTENT_EXTRACT_PATTERNS = [
    (r'AI摘要[^>]*内容由AI生成[^>]*"([^"]{20,})"', re.DOTALL),
    (r'(快科技\d{1,2}月\d{1,2}日[^科][^计][^详][^细][^文][^件][^管][^热][^好][^问][^相][^删].*?【本文结束】)', re.DOTALL),
    (r'<article[^>]*>(.*?)</article>', re.DOTALL),
    (r'(?:class|id)=["\'][^"\']*(?:article|content|post|entry)[^"\']*["\'][^>]*>(.*?)(?:</div>|</article>)', re.DOTALL),
    (r'<div[^>]+class=["\'][^"\']*content[^"\']*["\'][^>]*>([\s\S]{200,})</div>', re.DOTALL),
]

# =============================================================================
# HTML 结构提取
# =============================================================================
HTML_EXTRACT_PATTERNS = [
    (r'<section[^>]*data-type=["\']rtext["\'][^>]*>(.*?)</section>', re.DOTALL),
    (r'<article[^>]*>(.*?)</article>', re.DOTALL),
    (r'(?:class|id)=["\'][^"\']*(?:article|content|post|entry)[^"\']*["\'][^>]*>(.*?)</(?:div|p|article)>', re.DOTALL),
    (r'<div[^>]+class=["\'][^"\']*content[^"\']*["\'][^>]*>([\s\S]{200,})</div>', re.DOTALL),
]

# =============================================================================
# API 内联 JS 检测
# =============================================================================
_API_CONTENT_PATTERN = re.compile(
    r'(api\.|NewVideo/getVideoListByColumn|\.ajax|fetch\(|axios\.|XMLHttpRequest|getApiContent)',
    re.IGNORECASE
)

# =============================================================================
# $ .ajax 配置解析
# =============================================================================
_AJAX_CONFIG_PATTERN = re.compile(
    r'\$\.ajax\s*\(\s*\{([^}]+(?:\{[^}]*\}[^}]*)*)\}\s*\)',
    re.DOTALL
)
_JQ_SIMPLE_PATTERN = re.compile(
    r'\$\.(getJSON|get|post)\s*\(\s*["\']([^"\']+)["\']',
    re.DOTALL
)
_FETCH_PATTERN = re.compile(r'fetch\s*\(\s*["\']([^"\']+)["\']', re.DOTALL)
_URL_VAR_PATTERN = re.compile(
    r'(?:var\s+\w+\s*=\s*["\'])(//?[a-zA-Z0-9][^"\']*api[^\"\']*)["\']',
    re.DOTALL
)
_CNTV_API_PATTERN = re.compile(r'api\.cntv\.cn/[a-zA-Z0-9/_\-?&=\.]+', re.IGNORECASE)

# =============================================================================
# $ .ajax URL/参数解析
# =============================================================================
_AJAX_URL_PATTERN = re.compile(r'url\s*:\s*(?:["\']([^"\']+)["\']|(\w+))')
_AJAX_TYPE_PATTERN = re.compile(r'type\s*:\s*["\'](\w+)["\']')
_AJAX_DATATYPE_PATTERN = re.compile(r'dataType\s*:\s*["\'](\w+)["\']')
_AJAX_JSONP_CALLBACK = re.compile(r'jsonpCallback\s*:\s*["\'](\w+)["\']')
_AJAX_PARAMS_PATTERN = re.compile(
    r'(?:id|cid|category|page|pageNum|pageSize|num|count|sort|order|type|bd|serviceId)[\s:]',
    re.IGNORECASE
)

# =============================================================================
# 属性清洗：只保留 class, id, href, src
# 其他属性（含 data-*）全部删除——data-* 多用于前端跟踪/状态，对选择器定位无用
# =============================================================================
_ATTR_REMOVE_RE = re.compile(
    r'\s+(?!class\b|id\b|href\b|src\b|data-|value\b|type\b|name\b)(?:[a-z][a-z0-9:-]*)="[^"]*"',
    re.IGNORECASE
)
_ATTR_REMOVE_LINKLESS_RE = re.compile(
    r'\s+(?!class\b|id\b)(?:[a-z][a-z0-9:-]*)="[^"]*"',
    re.IGNORECASE
)

# =============================================================================
# 文章链接提取
# =============================================================================
_ARTICLE_URL_RE = re.compile(r'https?://[^\s<>"]+/[0-9]{8}/[a-z0-9_]+\.s?html?', re.I)
_SCRIPT_TAG_RE = re.compile(r'<script[^>]*>(.*?)</script>', re.DOTALL | re.IGNORECASE)
_MARKDOWN_TITLE_URL_RE = re.compile(r'\[([^\]]+)\]\((https?://\S+)(?:\s+[^)]+)?\)')
_HTTP_PREFIX_RE = re.compile(r'https?://')
_HEADER_START_RE = re.compile(r'^#+\s*\[?[\w]')
_EXT_TRAILING_RE = re.compile(r'\.(\w{3,10})\s*$')
_TITLE_PREFIX_RE = re.compile(r'^\s*[\]\)>}\-|:：\s\d*[:：\s]*')

# =============================================================================
# Boilerplate 行判断
# =============================================================================
_LINE_SEP_RE = re.compile(r'^[|\-=•○●◆■□▪▫◦▪*]{3,}$')
_LINE_FOREIGN_RE = re.compile(r'^[a-zA-Z0-9\s\(\)\.,;:!?-]+$')
_LINE_LINK_RE = re.compile(r'\[[^\]]*\]\([^)]+\)|<a[^>]*>[^<]*</a>')
_LINK_STRIP_RE = re.compile(r'[\[\](){}<>`]')
_LINE_CN_RE = re.compile(r'[\u4e00-\u9fff]')
_LINE_FOREIGN_COUNT_RE = re.compile(r'[a-zA-Z0-9]')
_LINE_PUNCT_RE = re.compile(r'[。！？！？\.!?]$')

# =============================================================================
# Boilerplate 日期行
# =============================================================================
_BP_DATE_RE = re.compile(r'^\d{4}[-/年]\d{1,2}[-/月]\d{1,2}[日]?\s*\d{1,2}:\d{2}')