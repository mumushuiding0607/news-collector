# Sources 配置 Tab 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 admin 前端后台配置页面新增 Sources Tab，可编辑保存 `backend/config/sources.json` 爬虫配置。

**Architecture:** 后端新增 `GET/POST /api/config/sources` 端点读写 `sources.json`；前端在 `/config` 页面新增 Tab 页，通过结构化表单展示和编辑配置。

**Tech Stack:** FastAPI (Python), Vue 3 + Element Plus (admin 前端)

## Global Constraints

- 后端所有脚本开头：`from script.bootstrap import *`
- 数据库操作必须通过 `script.db` 模块
- 前端组件通过 props/emit 或 store 通信
- LLM 调用必须串行（禁止 asyncio.gather）

---

## Task 1: 后端 - 在 config_service.py 中添加 sources 配置读写函数

**Files:**
- Modify: `backend/core/config_service.py`

**Interfaces:**
- Produces: `get_sources_config()` → `dict`, `update_sources_config(updates: dict)` → `dict`

- [ ] **Step 1: 在 config_service.py 末尾添加 sources 相关函数**

在 `backend/core/config_service.py` 文件末尾（在 `update_app_version_config` 函数之后）添加：

```python
def get_sources_config() -> dict:
    """获取 sources.json 爬虫配置"""
    sources_path = _PROJECT_ROOT / "backend" / "config" / "sources.json"
    return _load_json_config(sources_path)


def update_sources_config(updates: dict) -> dict:
    """
    更新 sources.json 爬虫配置（部分更新，深度合并嵌套 dict）
    例如：update_sources_config({"crawNumPerSource": 50})
    例如：update_sources_config({"newsCache": {"minScore": 10}})
    """
    sources_path = _PROJECT_ROOT / "backend" / "config" / "sources.json"
    current = _load_json_config(sources_path)
    current = _deep_merge(current, updates)
    _save_json_config(sources_path, current)
    return current
```

- [ ] **Step 2: 验证路径正确**

确认 `_PROJECT_ROOT` 指向项目根目录，`sources_path` 路径为 `{项目根}/backend/config/sources.json`，与现有 `sources.json` 实际位置一致。

- [ ] **Step 3: 提交**

```bash
git add backend/core/config_service.py
git commit -m "feat: add get_sources_config and update_sources_config"
```

---

## Task 2: 后端 - 在 config_api.py 中添加 sources 路由

**Files:**
- Modify: `backend/api/config_api.py`

**Interfaces:**
- Consumes: `get_sources_config`, `update_sources_config` from `core.config_service`
- Produces: `GET /config/sources`, `POST /config/sources` 端点

- [ ] **Step 1: 在 import 中添加新函数**

在 `backend/api/config_api.py` 的 import 部分，找到：
```python
from core.config_service import (
    get_app_config, update_app_config,
    get_env_config, update_env_config,
    get_full_config, get_public_config,
    get_app_version_config, update_app_version_config,
)
```

添加 `get_sources_config, update_sources_config`：
```python
from core.config_service import (
    get_app_config, update_app_config,
    get_env_config, update_env_config,
    get_full_config, get_public_config,
    get_app_version_config, update_app_version_config,
    get_sources_config, update_sources_config,
)
```

- [ ] **Step 2: 在路由文件末尾添加两个新端点**

在 `backend/api/config_api.py` 末尾（`update_subscription_tiers` 函数之后）添加：

```python
@router.get("/sources")
def get_config_sources(request: Request):
    """获取 sources.json 爬虫配置"""
    require_admin(request)
    return get_sources_config()


@router.post("/sources")
def update_config_sources(request: Request, updates: dict):
    """
    更新 sources.json 爬虫配置（部分更新）
    传入 {"crawNumPerSource": 50} 或 {"newsCache": {"minScore": 10}}
    """
    require_admin(request)
    try:
        return update_sources_config(updates)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
```

- [ ] **Step 3: 提交**

```bash
git add backend/api/config_api.py
git commit -m "feat: add GET/POST /config/sources endpoints"
```

---

## Task 3: 前端 - 在 config.ts 中添加 sources API 方法

**Files:**
- Modify: `admin/src/api/modules/config.ts`

**Interfaces:**
- Consumes: `api` client instance
- Produces: `getSourcesConfig()`, `updateSourcesConfig(data: Record<string, unknown>)`

- [ ] **Step 1: 在 config.ts 末尾添加 sources 相关 API**

在 `admin/src/api/modules/config.ts` 末尾添加：

```typescript
export const getSourcesConfig = () => api.get("/api/config/sources");

export const updateSourcesConfig = (data: Record<string, unknown>) =>
  api.post("/api/config/sources", data);
```

- [ ] **Step 2: 提交**

```bash
git add admin/src/api/modules/config.ts
git commit -m "feat: add getSourcesConfig and updateSourcesConfig API"
```

---

## Task 4: 前端 - 在 config/index.vue 中新增 Sources Tab

**Files:**
- Modify: `admin/src/views/config/index.vue`

**Interfaces:**
- Consumes: `getSourcesConfig`, `updateSourcesConfig` from `api/modules/config`
- Produces: 新增 "Sources 配置" Tab 页，含结构化表单

- [ ] **Step 1: 添加 sources 相关状态和表单**

在 `<script setup>` 中：
1. 导入 `getSourcesConfig, updateSourcesConfig`
2. 添加 `sourcesForm` ref，结构对应 sources.json 所有字段
3. 添加 `handleSaveSources` 函数

`sourcesForm` 结构：
```typescript
const sourcesForm = ref({
  crawNumPerSource: 30,
  maxConsecutiveNonToday: 10,
  llmBatchSize: 20,
  llmTimeout: 120,
  llmMaxRetries: 3,
  newsFilterTimeout: 40,
  scorerTimeout: 90,
  findStocksTimeout: 80,
  newsCache: {
    minScore: 5,
    hotNewsMinScore: 8,
    historyDays: 3,
  },
});
```

在 `fetchConfig()` 中并行获取 app、env、sources 三份配置：
```typescript
const [appData, envData, sourcesData] = await Promise.all([
  getAppConfig() as unknown as Promise<Record<string, unknown>>,
  getEnvConfig() as unknown as Promise<Record<string, unknown>>,
  getSourcesConfig() as unknown as Promise<Record<string, unknown>>,
]);
// ... 现有 app/env 逻辑
if (sourcesData) {
  sourcesForm.value = {
    crawNumPerSource: sourcesData["crawNumPerSource"] ?? 30,
    maxConsecutiveNonToday: sourcesData["maxConsecutiveNonToday"] ?? 10,
    llmBatchSize: sourcesData["llmBatchSize"] ?? 20,
    llmTimeout: sourcesData["llmTimeout"] ?? 120,
    llmMaxRetries: sourcesData["llmMaxRetries"] ?? 3,
    newsFilterTimeout: sourcesData["newsFilterTimeout"] ?? 40,
    scorerTimeout: sourcesData["scorerTimeout"] ?? 90,
    findStocksTimeout: sourcesData["findStocksTimeout"] ?? 80,
    newsCache: {
      minScore: sourcesData["newsCache"]?.["minScore"] ?? 5,
      hotNewsMinScore: sourcesData["newsCache"]?.["hotNewsMinScore"] ?? 8,
      historyDays: sourcesData["newsCache"]?.["historyDays"] ?? 3,
    },
  };
}
```

`handleSaveSources`：
```typescript
async function handleSaveSources() {
  saving.value = true;
  try {
    await updateSourcesConfig(sourcesForm.value);
    alert("Sources 配置保存成功");
  } catch (e) {
    console.error(e);
    alert("保存失败");
  } finally {
    saving.value = false;
  }
}
```

- [ ] **Step 2: 在模板中添加 Sources Tab**

在 `</el-tabs>` 之前（在 `</el-tab-pane>` 环境变量之后）添加：

```html
<el-tab-pane label="Sources 配置" name="sources">
  <el-card style="background: var(--card-bg); border: 1px solid var(--border); border-radius: 12px">
    <el-form :model="sourcesForm" label-width="160px" style="max-width: 700px">
      <el-divider content-position="left">采集参数</el-divider>
      <el-form-item label="每源采集数量">
        <el-input-number v-model="sourcesForm.crawNumPerSource" :min="1" :max="1000" />
      </el-form-item>
      <el-form-item label="最大连续非当日数">
        <el-input-number v-model="sourcesForm.maxConsecutiveNonToday" :min="1" :max="100" />
      </el-form-item>

      <el-divider content-position="left">LLM 参数</el-divider>
      <el-form-item label="LLM 批次大小">
        <el-input-number v-model="sourcesForm.llmBatchSize" :min="1" :max="200" />
      </el-form-item>
      <el-form-item label="LLM 超时（秒）">
        <el-input-number v-model="sourcesForm.llmTimeout" :min="10" :max="600" />
      </el-form-item>
      <el-form-item label="LLM 最大重试">
        <el-input-number v-model="sourcesForm.llmMaxRetries" :min="0" :max="10" />
      </el-form-item>

      <el-divider content-position="left">超时配置</el-divider>
      <el-form-item label="新闻过滤超时（秒）">
        <el-input-number v-model="sourcesForm.newsFilterTimeout" :min="5" :max="300" />
      </el-form-item>
      <el-form-item label="评分超时（秒）">
        <el-input-number v-model="sourcesForm.scorerTimeout" :min="5" :max="300" />
      </el-form-item>
      <el-form-item label="找股票超时（秒）">
        <el-input-number v-model="sourcesForm.findStocksTimeout" :min="5" :max="300" />
      </el-form-item>

      <el-divider content-position="left">缓存配置</el-divider>
      <el-form-item label="最低分数">
        <el-input-number v-model="sourcesForm.newsCache.minScore" :min="0" :max="100" />
      </el-form-item>
      <el-form-item label="热点新闻最低分">
        <el-input-number v-model="sourcesForm.newsCache.hotNewsMinScore" :min="0" :max="100" />
      </el-form-item>
      <el-form-item label="历史天数">
        <el-input-number v-model="sourcesForm.newsCache.historyDays" :min="1" :max="30" />
      </el-form-item>

      <el-form-item>
        <el-button type="primary" :loading="saving" @click="handleSaveSources">保存配置</el-button>
      </el-form-item>
    </el-form>
  </el-card>
</el-tab-pane>
```

- [ ] **Step 3: 提交**

```bash
git add admin/src/views/config/index.vue
git commit -m "feat: add Sources config tab in admin config page"
```

---

## Task 5: 验证

- [ ] 启动后端：`cd backend && python -m uvicorn backend.main:app --reload`
- [ ] 访问前端 `/config` 页面，确认新增 "Sources 配置" Tab 可见
- [ ] 点击 Tab，验证表单初始值与 `sources.json` 当前值一致
- [ ] 修改任意字段，点击保存，验证 `sources.json` 文件已更新
- [ ] 刷新页面，验证数据正确回显

---

## Spec Self-Review

1. **Spec coverage:** sources.json 所有字段（9个顶层 + 3个 newsCache 嵌套）均已在表单中覆盖 ✓
2. **Placeholder scan:** 无 TBD/TODO，所有代码片段完整 ✓
3. **Type consistency:** 后端函数签名与前端 API 调用匹配，字段名完全一致 ✓
