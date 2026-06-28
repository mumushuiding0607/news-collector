"""
anomaly_news - 异动消息处理模块

公共接口：
  fetcher.discover_and_save(url)  - 采集异动消息并保存
  confirm.confirm_sources()        - 确认数据源
  learn.run()                      - 学习数据源配置
  summary.generate()               - 生成异动简报
  pipeline.run()                   - 完整流程编排
"""
from script.anomaly_news.pipeline import run_pipeline

__all__ = ['run_pipeline']
