"""
anomaly_news/scheduler.py - 异动消息定时任务入口

周一至周五 11:30 和 16:00 执行异动消息采集。
"""
from script.log import log as _log, init_log


def log(msg: str):
    _log("anomaly_scheduler", msg)


def run():
    """定时任务入口：采集异动消息入库"""
    init_log()
    log("[定时任务] 开始执行异动消息采集")

    from script.anomaly_news.fetcher import discover_and_save
    url = 'https://yuanchuang.10jqka.com.cn/mrnxgg_list/index_2.shtml'
    result = discover_and_save(url)

    if 'error' in result:
        log(f"[定时任务] 错误: {result['error']}")
        return

    log(f"[定时任务] 完成: 抓取 {result.get('total_anomalies')} 条，保存 {result.get('saved')} 条，发现 {len(result.get('discovered_sources', []))} 个数据源")


if __name__ == '__main__':
    run()
