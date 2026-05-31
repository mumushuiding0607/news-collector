# News Board - 市场热点追踪应用

Flutter 实现的新闻看板前端，支持板块涨跌、核心标的查询。

## 快速启动

### 后端（FastAPI）

```bash
cd C:\Users\18145\.openclaw\workspace\新闻采集\backend
python main.py
```

后端运行在 `http://localhost:3000`

### 前端（Flutter Web）

```bash
cd C:\Users\18145\.openclaw\workspace\新闻采集\news_board_app
flutter run -d chrome
```

或启动热重载开发服务器：

```bash
cd C:\Users\18145\.openclaw\workspace\新闻采集\news_board_app
flutter run -d chrome --web-port=5173
```

### 同时启动前后端

终端1：
```bash
cd C:\Users\18145\.openclaw\workspace\新闻采集\backend && python main.py
```

终端2：
```bash
cd C:\Users\18145\.openclaw\workspace\新闻采集\news_board_app && flutter run -d chrome
```

## 项目结构

```
news_board_app/
├── lib/
│   ├── main.dart           # 应用入口
│   ├── home_page.dart      # 首页
│   ├── api_service.dart    # API 调用
│   └── widgets/            # UI 组件
├── pubspec.yaml            # 依赖配置
└── README.md
```

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/health | 健康检查 |
| GET | /api/rag/sectors | 查询所有板块 |
| GET | /api/rag/stocks?sector=xxx | 按板块查询核心标的 |
| GET | /api/rag/stocks/by-sector/{name} | 按板块名查询 |
| POST | /api/rag/parse | 解析报告入库 |

## 技术栈

- Flutter 3.12+ / Dart 3
- FastAPI (Python)
- HTTP 请求