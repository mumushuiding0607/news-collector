"""
source_discovery 定时任务调度接口

周一至周五 11:30 和 16:00 执行异动消息数据源发现
"""
from .source_finder import discover_sources
from script.log import log as _log, init_log


def log(msg: str):
    _log("source_discovery", msg)


def discover_and_schedule():
    """
    定时任务入口：发现异动消息数据源并保存到数据库
    周一至周五 11:30 和 16:00 执行
    """
    init_log()
    log("[定时任务] 开始执行异动消息数据源发现")

    # 同花顺异动消息页面
    url = 'https://yuanchuang.10jqka.com.cn/mrnxgg_list/index_2.shtml'

    result = discover_sources(url, save_to_db=True)

    if 'error' in result:
        log(f"[定时任务] 错误: {result['error']}")
        return

    log(f"[定时任务] 完成: 发现 {len(result.get('discovered_sources', []))} 个数据源")


if __name__ == '__main__':
    discover_and_schedule()