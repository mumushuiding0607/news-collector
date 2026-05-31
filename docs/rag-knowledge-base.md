# 核心标的 RAG 知识库

## 背景

基于《核心标的筛选提示词》生成的报告，设计结构化知识库，实现快速筛选。

## 设计原则

- **生成时解析**：报告生成后一次性解析入库，LLM 仅调用一次
- **查询时纯SQL**：无需 LLM，token 消耗 = 0
- **结构化存储**：支持多维度筛选

## 数据库设计

### sectors - 板块表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| name | TEXT | 板块名称（如"新能源汽车"）|
| chain_structure | TEXT | 产业链9环节覆盖情况（JSON）|
| created_at | TEXT | 创建时间 |

### stocks - 核心标的表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| sector_id | INTEGER | 所属板块 |
| code | TEXT | 股票代码 |
| name | TEXT | 股票名称 |
| tier | TEXT | 梯队（第一/第二/第三梯队A/B）|
| chain_link | TEXT | 产业环节 |
| four_dims | TEXT | 四维度评分（JSON：竞争/盈利/客户/技术）|
| moat | TEXT | 核心护城河 |
| q1_metrics | TEXT | Q1关键业绩 |
| include_path | TEXT | 纳入路径 |
| created_at | TEXT | 创建时间 |

### eliminated_stocks - 已剔除标的表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| sector_id | INTEGER | 所属板块 |
| code | TEXT | 股票代码 |
| name | TEXT | 股票名称 |
| reason | TEXT | 剔除原因 |
| rule_no | TEXT | 规则编号 |
| created_at | TEXT | 创建时间 |

## 实现步骤

### 1. 数据库 schema
- 创建 sectors/stocks/eliminated_stocks 表

### 2. 报告解析器
- 解析正文表格 → stocks 表
- 解析附录一 → eliminated_stocks 表
- 解析附录二 → sectors.chain_structure

### 3. API 接口
- POST /api/rag/parse - 解析报告入库
- GET /api/rag/stocks - 按板块查询核心标的
- GET /api/rag/sectors - 查询所有板块

### 4. 前端页面（可选）
- 板块筛选页面
- 标的详情页面