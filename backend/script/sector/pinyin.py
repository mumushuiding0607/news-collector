"""
sector_pinyin.py - 拼音转换工具

被 sectors.py、sectors_crud.py、sector_matcher.py 共用。
"""

try:
    from pypinyin import lazy_pinyin

    def to_pinyin_initial(text: str) -> str:
        if not text:
            return ""
        py = lazy_pinyin(text)
        return "".join(w[0] if w else "" for w in py)

    def to_pinyin_full(text: str) -> str:
        if not text:
            return ""
        return "".join(lazy_pinyin(text))

except ImportError:
    def to_pinyin_initial(text: str) -> str:
        return ""
    def to_pinyin_full(text: str) -> str:
        return ""
    print("[警告] pypinyin 未安装，拼音匹配功能不可用。请运行: pip install pypinyin")