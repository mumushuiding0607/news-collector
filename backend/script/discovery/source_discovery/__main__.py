"""
数据源发现模块入口

用法：
    python -m script.discovery.source_discovery <URL> [--save]
"""
from .cli import main

if __name__ == '__main__':
    main()