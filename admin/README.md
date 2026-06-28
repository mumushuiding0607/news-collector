# 新闻看板管理后台 (Admin)

Vue 3 + Element Plus 管理后台，提供订阅管理、用户管理、配置管理、定时任务、日志查看等功能。

## 快速启动

```bash
# 安装依赖
npm install

# 启动开发服务器
npm run dev

# 构建生产版本
npm run build
```

## 环境要求

- Node.js 16+
- pnpm 或 npm

## 项目结构

```
admin/
├── src/
│   ├── api/              # API 接口封装
│   ├── layout/          # 布局组件
│   ├── router/          # 路由配置
│   ├── stores/          # 状态管理
│   └── views/           # 页面组件
│       ├── config/      # 后台配置
│       ├── dashboard/   # 控制台
│       ├── feedback/    # 反馈管理
│       ├── logs/        # 日志管理
│       ├── news/        # 新闻管理
│       ├── schedule/    # 定时任务
│       ├── subscription/# 订阅管理
│       └── user/        # 用户管理
├── public/
└── package.json
```

## 功能模块

| 模块 | 说明 |
|------|------|
| 控制台 | 系统概览 |
| 新闻管理 | 查看和管理新闻数据 |
| 用户管理 | 用户列表、订阅等级修改 |
| 订阅管理 | 订阅等级修改、待确认用户确认 |
| 反馈管理 | 用户反馈查看和回复 |
| 后台配置 | 应用配置和环境变量管理 |
| 定时任务 | 定时任务的新增、修改、删除、触发 |
| 日志管理 | 按日期查看日志文件内容 |

## 后端 API

管理后台依赖后端服务，需要先启动后端：

```bash
cd backend
pip install -r requirements.txt
python main.py
```

后端服务默认运行在 `http://localhost:31234`

## 开发说明

- 前端代码只负责展示和用户交互
- 所有业务逻辑和数据处理都在后端 `backend/` 目录
- 新增功能需要同时更新前端和后端
- 遵循 BEST_PRACTICE.md 中的代码规范