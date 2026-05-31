# Python 项目最佳实践

## 一、模块设计原则

### 1.1 单一职责
- 每个模块只做一件事，且做到最好
- 模块名应该清晰表达它的职责
- 对外暴露最简单的接口，内部细节对调用方透明

### 1.2 目录结构规范
```
project/
├── 模块A/              # 按领域分组，不是按类型
│   ├── __init__.py
│   ├── service.py      # 业务逻辑
│   ├── model.py        # 数据模型
│   └── api.py          # 接口（如果需要）
├── common/             # 只有2个以上模块共用才放这里
├── tests/              # 和源码对应目录结构
└── pyproject.toml
```

### 1.3 导入顺序（PEP8）
```python
# 1. 标准库
import os
import sys
from datetime import datetime

# 2. 第三方库
import httpx
from pydantic import BaseModel

# 3. 本地导入（相对优先）
from .common import config
from ..api import router
```

## 二、函数设计原则

### 2.1 函数规范
```python
# ✅ 好的函数：单一职责，名字自解释，有文档字符串
def fetch_news_list(source: str, limit: int = 20) -> list[dict]:
    """从指定来源获取新闻列表

    Args:
        source: 新闻来源标识
        limit: 最大返回条数

    Returns:
        新闻字典列表，按发布时间倒序
    """
    pass

# ❌ 坏的函数：做什么看不出来，参数复杂
def get(data, flag=True, timeout=60):
    pass
```

### 2.2 参数设计
- 必须有关键字参数：`def func(*, required_arg, optional_arg=default)`
- 布尔参数用 `flag` 或 `is_` 开头命名
- 避免超过 4 个参数，考虑封装成配置类

### 2.3 返回值
- 始终返回一致的数据结构
- 失败返回 `None` 或抛异常，不返回特殊值
- 文档中明确说明可能返回 `None`

## 三、错误处理原则

### 3.1 异常规范
```python
# ✅ 自定义异常类，继承正确的基类
class NewsFetchError(Exception):
    """新闻获取失败"""
    pass

class LLMCallError(Exception):
    """LLM 调用失败"""
    pass

# ❌ 避免 bare except，捕获具体异常
try:
    await call_llm(prompt)
except httpx.TimeoutException:
    logger.warning("LLM 调用超时")
except httpx.HTTPError as e:
    logger.error(f"LLM HTTP 错误: {e}")
```

### 3.2 错误传播
- 底层异常在传播时补充上下文，不要吞掉
- `raise NewError("描述") from original_error`

## 四、命名规范

### 4.1 命名风格
| 类型 | 风格 | 示例 |
|------|------|------|
| 模块/包 | 小写下划线 | `rag_service.py` |
| 类 | 大驼峰 | `class NewsService` |
| 函数/变量 | 小写下划线 | `fetch_news()` |
| 常量 | 大写下划线 | `MAX_RETRIES` |
| 私有成员 | 下划线开头 | `_private_func()` |

### 4.2 命名自解释
```python
# ✅ 好：一看就知道干什么
def calculate_news_score(news_text: str, sector: str) -> int:

# ❌ 差：需要读实现才知道
def calc(t, s) -> int:
```

## 五、代码组织

### 5.1 服务类模式
```python
# ✅ 一个服务类聚合相关功能
class NewsService:
    def __init__(self, config: AppConfig):
        self._config = config
        self._cache = Cache()

    def fetch_latest(self) -> list[NewsItem]:
        ...

    def fetch_history(self, days: int = 3) -> list[NewsItem]:
        ...
```

### 5.2 避免循环导入
```
A.py → B.py → A.py  ❌ 循环
A.py → common.py → B.py  ✅ 通过 common 中转
```

## 六、配置管理

### 6.1 配置分离
```python
# config.py - 配置类
from pydantic import BaseModel

class AppConfig(BaseModel):
    llm_timeout: int = 60
    cache_ttl: int = 300
    max_retries: int = 3

# 环境变量覆盖
import os
config = AppConfig(
    llm_timeout=int(os.getenv("LLM_TIMEOUT", 60))
)
```

### 6.2 硬编码要抽离
```python
# ❌ 硬编码
if sector == "建筑装饰":

# ✅ 配置化
ALLOWED_SECTORS = ["建筑装饰", "房地产", ...]
if sector in ALLOWED_SECTORS:
```

## 七、日志规范

```python
import logging

logger = logging.getLogger(__name__)

def func():
    logger.debug("详细调试信息")
    logger.info("正常流程信息")
    logger.warning("警告但可继续")
    logger.error("错误需要关注")
```

### 7.1 文件生成位置
- **所有 log 文件必须在 `logs/` 目录中生成**
- **所有 test 文件必须在 `test/` 目录或对应模块的 `test/` 子目录中生成**
- 禁止在业务代码目录中直接创建 log 或 test 文件

```python
# ✅ 正确
from pathlib import Path
log_dir = Path(__file__).parent.parent / "logs"
log_file = log_dir / "app.log"

# ❌ 错误 - 在业务目录中生成
log_file = Path(__file__).parent / "debug.log"
```

## 八、重构检查清单

开始重构前确认：
- [ ] 为什么需要重构？问题是什么？
- [ ] 重构的边界在哪里？只改这一个模块还是连锁改动？
- [ ] 是否有测试覆盖？能否快速验证？
- [ ] 能否小步提交？每次只改一件事

重构后检查：
- [ ] 函数是否单一职责？
- [ ] 命名是否自解释？
- [ ] 是否有足够的文档字符串？
- [ ] 错误处理是否完善？
- [ ] 是否有冗余代码？
- [ ] 循环导入是否消除？

## 九、Git 提交规范

```
feat: 新功能
fix: 修复 bug
refactor: 重构（不改变功能）
docs: 文档
test: 测试
chore: 构建/工具
```

## 十、常见反模式

| 反模式 | 问题 | 替代方案 |
|--------|------|----------|
| 神类 (God Class) | 一个类做太多事 | 按职责拆分 |
| 重复代码 | 修改要改多处 | 抽象成公共函数 |
| 深度嵌套 | 难以阅读 | 早返回/提取函数 |
| 神秘命名 | 不知道干什么 | 重命名为自解释 |
| 全局状态 | 难以追踪 | 依赖注入 |