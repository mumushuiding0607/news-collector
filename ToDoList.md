1. 在publish/admin目录下生成部署文件，将admin项目build之后部署到远程服务器并运行
2. 重新部署backend到服务器
3. 推送db到服务器

---

## 验证 + 反馈学习模块

**背景**：Pipeline 跑完后能验证 LLM 预测（评分、方向、核心标的）与实际涨幅的匹配度，并通过历史验证结果驱动下次预测更准确。

### 外部依赖（需外部实现）

**API 1：Lesson 生成**
```
POST /api/rag/generate-lesson
Body: {title, sectors, llm_score, llm_direction, llm_intensity,
       llm_expected_change, actual_max_rise, tier1_avg_rise, d1, d2, d3}
Response: {lesson: str}
```

**API 2：相似 Lesson 检索**
```
POST /api/rag/retrieve-lessons
Body: {query: str, lessons: [...], top_k: int}
Response: {lessons: [{title, lesson, llm_score, actual_max_rise, similarity_score}, ...]}
```

### 项目内新增文件

| 文件 | 作用 |
|------|------|
| `backend/script/db/verification.py` | 验证结果 CRUD + lesson 查询接口 |
| `backend/script/verify/verify_stocks.py` | 验证入口脚本 |
| `backend/script/verify/lesson_generator.py` | 外部 RAG API 调用封装 |
| `backend/script/common/change_rate.py` | 涨跌幅解析 `"+2.35%"` → `2.35` |
| `backend/prompt/预测验证.md` | 验证分析提示词（给外部 API 参考） |
| `backend/prompt/lesson生成.md` | lesson 生成提示词（给外部 API 参考） |

### 项目内修改文件

| 文件 | 改动 |
|------|------|
| `backend/script/db/schema.sql` | 新增 `verification_results` 表 |
| `backend/script/score/scorer.py` | LLM 调用前查 lesson 并注入 prompt |
| `backend/script/stock/find_stocks_logic.py` | LLM 调用前查 lesson 并注入 prompt |
| `backend/prompt/事件评估.md` | 加 `<<lessons>>` 占位符 |
| `backend/prompt/核心标的.md` | 加 `<<lessons>>` 占位符 |
| `backend/config/sources.json` | 新增 `externalRagApi` 配置项 |

### 新增 DB 表

```sql
CREATE TABLE verification_results (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  importance_id INTEGER NOT NULL UNIQUE,
  title TEXT,
  related_sectors TEXT,
  llm_score INTEGER,
  llm_direction TEXT,
  llm_intensity INTEGER,
  llm_expected_change TEXT,
  actual_max_rise REAL,
  actual_d1 REAL,
  actual_d2 REAL,
  actual_d3 REAL,
  tier1_avg_rise REAL,
  tier1_count INTEGER,
  direction_match INTEGER,
  score_match INTEGER,
  lesson TEXT,
  verified_at TEXT,
  created_at TEXT,
  FOREIGN KEY (importance_id) REFERENCES importance(id)
);
CREATE INDEX idx_vr_sectors ON verification_results(related_sectors);
CREATE INDEX idx_vr_score ON verification_results(llm_score);
CREATE INDEX idx_vr_created ON verification_results(created_at);
```

### 验证流程

```
verify_stocks.py --days 5
  1. 查 news_stocks 中 d1/d2/d3 至少一个非 NULL 且无 vr 记录的 importance_id
  2. 读 importance（LLM预测） + news_stocks（实际涨跌幅）
  3. 计算 actual_max_rise、direction_match、score_match
  4. 调用外部 RAG API 生成 lesson
  5. 写入 verification_results
```

### 预测时 lesson 注入流程

```
scorer / findStocks LLM 调用前：
  1. 查 verification_results 所有有 lesson 的记录
  2. 发给外部 RAG API → 返回相似度排序的 top-k lessons
  3. 格式化为文本块注入 <<lessons>> 占位符
  4. 调用 LLM（prompt 已含历史教训）
```

### 运行方式

```bash
# 每天 16:10 验证
python -m script.verify.verify_stocks --days 5

# scorer / findStocks 自动注入 lesson
python -m script.score.scorer
python -m script.stock.find_stocks_logic
```