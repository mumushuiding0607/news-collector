"""
test_extract_content.py - extract_content_from_html 测试类

用法:
    python test_extract_content.py [html_file] [url]

示例:
    python test_extract_content.py ../logs/test.txt https://news.mydrivers.com/1/1125/1125742.htm
    python test_extract_content.py                          # 使用默认 test.txt
"""

import sys
import re
from pathlib import Path
from datetime import datetime

# 添加 common 到路径
sys.path.insert(0, str(Path(__file__).parent))
from common.util import extract_content_from_html


class ContentExtractorTest:
    """测试 extract_content_from_html 方法"""

    def __init__(self, html_file: str = None, url: str = None, log_file: str = None):
        self.html_file = html_file or self._default_html_file()
        self.url = url or "https://news.mydrivers.com/1/1125/1125742.htm"
        self.log_file = log_file or self._default_log_file()

    def _default_html_file(self) -> str:
        return str(Path(__file__).parent / "../logs/test.txt")

    def _default_log_file(self) -> str:
        return str(Path(__file__).parent / "../logs/test_extract.log")

    def run(self):
        """执行测试"""
        self._log(f"{'='*60}")
        self._log(f"测试开始: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self._log(f"{'='*60}")
        self._log(f"HTML文件: {self.html_file}")
        self._log(f"URL: {self.url}")
        self._log(f"日志文件: {self.log_file}")
        self._log("")

        # 读取 HTML 文件
        try:
            with open(self.html_file, encoding='utf-8') as f:
                html = f.read()
            self._log(f"[OK] 成功读取HTML文件，大小: {len(html)} 字节")
        except FileNotFoundError:
            self._log(f"[FAIL] 文件不存在: {self.html_file}")
            return
        except Exception as e:
            self._log(f"[FAIL] 读取文件失败: {e}")
            return

        # 调用 extract_content_from_html
        self._log("")
        self._log("调用 extract_content_from_html()...")
        try:
            result = extract_content_from_html(html, self.url)
            self._log("[OK] 方法调用成功")
        except Exception as e:
            self._log(f"[FAIL] 方法调用失败: {e}")
            return

        # 输出结果
        self._log("")
        self._log("-" * 40)
        self._log("返回结果:")
        self._log(f"  source:      {result['source']}")
        self._log(f"  raw_length:  {result['raw_length']} 字节")
        self._log(f"  ai_summary:  {len(result['ai_summary'])} 字")
        self._log(f"  content:      {len(result['content'])} 字")

        self._log("")
        self._log("-" * 40)
        self._log("AI摘要内容:")
        self._log(self._indent(result['ai_summary'][:500], 2))
        if len(result['ai_summary']) > 500:
            self._log("  ... (省略)")

        self._log("")
        self._log("-" * 40)
        self._log("正文内容 (前1000字):")
        self._log(self._indent(result['content'][:1000], 2))
        if len(result['content']) > 1000:
            self._log("  ... (省略)")

        self._log("")
        self._log("-" * 40)
        self._log("正文内容 (后500字):")
        if len(result['content']) > 500:
            self._log(self._indent(result['content'][-500:], 2))

        self._log("")
        self._log(f"{'='*60}")
        self._log(f"测试完成: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self._log(f"{'='*60}")

        # 写入完整日志
        self._write_full_log(html, result)

    def _log(self, msg: str):
        """输出到控制台和日志文件"""
        print(msg)
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(msg + "\n")

    def _indent(self, text: str, spaces: int = 2) -> str:
        """缩进文本"""
        indent = " " * spaces
        return "\n".join(f"{indent}{line}" for line in text.split("\n"))

    def _write_full_log(self, html: str, result: dict):
        """写入完整测试日志"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        full_log = Path(self.log_file).parent / f"test_extract_{timestamp}.log"

        content = []
        content.append("=" * 60)
        content.append("extract_content_from_html 完整测试报告")
        content.append("=" * 60)
        content.append(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        content.append(f"HTML文件: {self.html_file}")
        content.append(f"URL: {self.url}")
        content.append(f"HTML大小: {len(html)} 字节")
        content.append("")
        content.append("-" * 40)
        content.append("返回结果:")
        content.append(f"  source:      {result['source']}")
        content.append(f"  raw_length:  {result['raw_length']} 字节")
        content.append(f"  ai_summary:  {len(result['ai_summary'])} 字")
        content.append(f"  content:      {len(result['content'])} 字")
        content.append("")
        content.append("-" * 40)
        content.append("AI摘要:")
        content.append(result['ai_summary'])
        content.append("")
        content.append("-" * 40)
        content.append("正文内容:")
        content.append(result['content'])
        content.append("")
        content.append("=" * 60)

        with open(full_log, "w", encoding="utf-8") as f:
            f.write("\n".join(content))

        self._log(f"\n完整日志已写入: {full_log}")


def main():
    args = sys.argv[1:]

    if args:
        html_file = args[0]
        url = args[1] if len(args) > 1 else "https://news.mydrivers.com/1/1125/1125742.htm"
    else:
        html_file = None
        url = None

    tester = ContentExtractorTest(html_file=html_file, url=url)
    tester.run()


if __name__ == "__main__":
    main()
