# Flutter AI 协助开发一步步指引

> 本教程指导 AI 助手如何逐步完成 Flutter 新闻看板应用的开发

## 项目背景

- **项目名称**：新闻看板 (NewsBoard)
- **核心功能**：展示最新批次中高评分的新闻，帮助操盘手和散户快速捕捉市场热点
- **技术栈**：Flutter 3.x + Dart + Riverpod/Provider + Dio + SQLite

---

## 第一阶段：项目初始化与环境配置

### 1.1 检查开发环境

AI 助手应首先检查以下内容：

```bash
# 检查 Flutter 版本
flutter --version

# 检查 Dart 版本
dart --version

# 检查 Android SDK 配置
flutter doctor

# 检查项目依赖是否正常
cd 新闻采集 && flutter pub get
```

### 1.2 创建 Flutter 项目（如需全新项目）

```bash
cd 新闻采集
flutter create --org com.example --project-name news_board .
```

### 1.3 依赖配置

在 `pubspec.yaml` 中配置所需依赖：

```yaml
dependencies:
  flutter:
    sdk: flutter
  flutter_riverpod: ^2.4.0      # 状态管理
  dio: ^5.3.0                    # HTTP 请求
  sqflite: ^2.3.0               # 本地存储
  path: ^1.8.0                  # 路径处理
  intl: ^0.18.0                 # 日期格式化
  google_fonts: ^6.1.0          # 字体

dev_dependencies:
  flutter_test:
    sdk: flutter
  flutter_lints: ^3.0.0
```

**AI 操作指令**：更新 `pubspec.yaml` 后执行 `flutter pub get`

---

## 第二阶段：架构搭建

### 2.1 目录结构规划

按照 Clean Architecture 规划目录：

```
lib/
├── main.dart                      # 入口文件
├── app.dart                       # App 配置
├── core/
│   ├── theme/
│   │   └── app_theme.dart         # 主题配置
│   └── constants/
│       └── app_constants.dart     # 常量定义
├── data/
│   ├── models/                    # 数据模型
│   │   └── news_model.dart
│   └── repositories/              # 数据仓库实现
│       └── news_repository_impl.dart
├── domain/
│   ├── entities/                  # 业务实体
│   │   └── news_entity.dart
│   └── repositories/              # 仓库接口
│       └── news_repository.dart
├── presentation/
│   ├── pages/                    # 页面
│   │   ├── home_page.dart
│   │   └── detail_page.dart
│   ├── widgets/                  # 组件
│   │   ├── news_card.dart
│   │   ├── batch_info_card.dart
│   │   └── score_badge.dart
│   └── providers/                # Riverpod providers
│       └── news_provider.dart
└── shared/
    └── widgets/
        └── glass_card.dart        # 玻璃拟态卡片
```

### 2.2 核心文件创建顺序

1. **先创建实体层** (`domain/entities/`)
2. **再创建仓库接口** (`domain/repositories/`)
3. **然后数据模型** (`data/models/`)
4. **接着仓库实现** (`data/repositories/`)
5. **再创建主题** (`core/theme/`)
6. **最后 UI 层** (`presentation/`)

**AI 操作指令**：按顺序创建上述文件，每完成一层后汇报进度

---

## 第三阶段：UI 开发

### 3.1 主题配置

创建 `lib/core/theme/app_theme.dart`：

```dart
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

class AppTheme {
  static const Color background = Color(0xFF0D0D0D);
  static const Color backgroundGradientEnd = Color(0xFF1A1A1A);
  static const Color accentRed = Color(0xFFFF4444);
  static const Color accentGreen = Color(0xFF44FF44);
  static const Color textPrimary = Colors.white;
  static const Color textSecondary = Color(0xFF888888);

  static ThemeData get darkTheme {
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.dark,
      scaffoldBackgroundColor: background,
      colorScheme: const ColorScheme.dark(
        primary: accentRed,
        secondary: accentGreen,
        surface: Color(0xFF1A1A1A),
      ),
      textTheme: GoogleFonts.notoSansScTextTheme(
        const TextTheme(
          headlineLarge: TextStyle(color: textPrimary, fontSize: 28, fontWeight: FontWeight.bold),
          titleLarge: TextStyle(color: textPrimary, fontSize: 20),
          bodyLarge: TextStyle(color: textPrimary),
          bodyMedium: TextStyle(color: textSecondary),
        ),
      ),
      appBarTheme: const AppBarTheme(
        backgroundColor = Colors.transparent,
        elevation: 0,
      ),
    );
  }
}
```

### 3.2 玻璃拟态卡片组件

创建 `lib/shared/widgets/glass_card.dart`：

```dart
import 'dart:ui';
import 'package:flutter/material.dart';

class GlassCard extends StatelessWidget {
  final Widget child;
  final double borderRadius;
  final EdgeInsetsGeometry padding;

  const GlassCard({
    super.key,
    required this.child,
    this.borderRadius = 16,
    this.padding = const EdgeInsets.all(16),
  });

  @override
  Widget build(BuildContext context) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(borderRadius),
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 10, sigmaY: 10),
        child: Container(
          decoration: BoxDecoration(
            color: Colors.white.withOpacity(0.1),
            borderRadius: BorderRadius.circular(borderRadius),
            border: Border.all(color: Colors.white.withOpacity(0.1)),
          ),
          padding: padding,
        ),
      ),
    );
  }
}
```

### 3.3 新闻卡片组件

创建 `lib/presentation/widgets/news_card.dart`：

```dart
import 'package:flutter/material.dart';
import 'package:news_board/shared/widgets/glass_card.dart';
import 'package:news_board/presentation/widgets/score_badge.dart';

class NewsCard extends StatelessWidget {
  final String title;
  final double score;
  final List<String> sectors;
  final String summary;
  final VoidCallback onTap;

  const NewsCard({
    super.key,
    required this.title,
    required this.score,
    required this.sectors,
    required this.summary,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: GlassCard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    title,
                    style: const TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.bold,
                      color: Colors.white,
                    ),
                  ),
                ),
                ScoreBadge(score: score),
              ],
            ),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              children: sectors.map((s) => Chip(
                label: Text(s, style: const TextStyle(fontSize: 12)),
                backgroundColor: Colors.blue.withOpacity(0.3),
              )).toList(),
            ),
            const SizedBox(height: 8),
            Text(
              summary,
              style: const TextStyle(color: Color(0xFF888888)),
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
          ],
        ),
      ),
    );
  }
}
```

---

## 第四阶段：状态管理与数据获取

### 4.1 Riverpod Provider 创建

创建 `lib/presentation/providers/news_provider.dart`：

```dart
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:news_board/domain/entities/news_entity.dart';
import 'package:news_board/data/repositories/news_repository_impl.dart';

final newsRepositoryProvider = Provider<NewsRepository>((ref) {
  return NewsRepositoryImpl();
});

final newsListProvider = FutureProvider<List<NewsEntity>>((ref) async {
  final repository = ref.watch(newsRepositoryProvider);
  return repository.getLatestNews();
});

final selectedNewsProvider = StateProvider<NewsEntity?>((ref) => null);
```

### 4.2 数据仓库接口

创建 `lib/domain/repositories/news_repository.dart`：

```dart
import 'package:news_board/domain/entities/news_entity.dart';

abstract class NewsRepository {
  Future<List<NewsEntity>> getLatestNews();
  Future<NewsEntity?> getNewsById(int id);
}
```

### 4.3 数据仓库实现

创建 `lib/data/repositories/news_repository_impl.dart`：

```dart
import 'package:news_board/domain/entities/news_entity.dart';
import 'package:news_board/domain/repositories/news_repository.dart';
import 'package:news_board/data/models/news_model.dart';

class NewsRepositoryImpl implements NewsRepository {
  @override
  Future<List<NewsEntity>> getLatestNews() async {
    // TODO: 实现从 SQLite 或 API 获取数据的逻辑
    // 示例：从数据库读取
    final models = await _fetchFromDatabase();
    return models.map((m) => m.toEntity()).toList();
  }

  Future<List<NewsModel>> _fetchFromDatabase() async {
    // 实现数据库读取
    throw UnimplementedError();
  }

  @override
  Future<NewsEntity?> getNewsById(int id) async {
    throw UnimplementedError();
  }
}
```

---

## 第五阶段：页面开发

### 5.1 首页开发

创建 `lib/presentation/pages/home_page.dart`：

```dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:news_board/presentation/providers/news_provider.dart';
import 'package:news_board/presentation/widgets/news_card.dart';
import 'package:news_board/presentation/widgets/batch_info_card.dart';

class HomePage extends ConsumerWidget {
  const HomePage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final newsAsync = ref.watch(newsListProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('新闻看板'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => ref.invalidate(newsListProvider),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () async {
          ref.invalidate(newsListProvider);
        },
        child: newsAsync.when(
          data: (newsList) => ListView.builder(
            padding: const EdgeInsets.all(16),
            itemCount: newsList.length,
            itemBuilder: (context, index) {
              final news = newsList[index];
              return Padding(
                padding: const EdgeInsets.only(bottom: 16),
                child: NewsCard(
                  title: news.title,
                  score: news.importanceScore,
                  sectors: news.relatedSectors,
                  summary: news.summary,
                  onTap: () {
                    ref.read(selectedNewsProvider.notifier).state = news;
                    Navigator.pushNamed(context, '/detail');
                  },
                ),
              );
            },
          ),
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (err, stack) => Center(child: Text('Error: $err')),
        ),
      ),
    );
  }
}
```

### 5.2 详情页开发

创建 `lib/presentation/pages/detail_page.dart`：

```dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:news_board/presentation/providers/news_provider.dart';
import 'package:news_board/shared/widgets/glass_card.dart';

class DetailPage extends ConsumerWidget {
  const DetailPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final news = ref.watch(selectedNewsProvider);

    if (news == null) {
      return Scaffold(
        appBar: AppBar(title: const Text('详情')),
        body: const Center(child: Text('No news selected')),
      );
    }

    return Scaffold(
      appBar: AppBar(title: const Text('新闻详情')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              news.title,
              style: const TextStyle(
                fontSize: 24,
                fontWeight: FontWeight.bold,
                color: Colors.white,
              ),
            ),
            const SizedBox(height: 16),
            GlassCard(
              child: Text(
                news.summary,
                style: const TextStyle(color: Colors.white, fontSize: 16),
              ),
            ),
            const SizedBox(height: 16),
            ElevatedButton(
              onPressed: () {
                // TODO: 打开原文链接
              },
              child: const Text('查看原文'),
            ),
          ],
        ),
      ),
    );
  }
}
```

---

## 第六阶段：入口文件配置

### 6.1 main.dart

创建 `lib/main.dart`：

```dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:news_board/app.dart';

void main() {
  runApp(
    const ProviderScope(
      child: NewsBoardApp(),
    ),
  );
}
```

### 6.2 app.dart

创建 `lib/app.dart`：

```dart
import 'package:flutter/material.dart';
import 'package:news_board/core/theme/app_theme.dart';
import 'package:news_board/presentation/pages/home_page.dart';
import 'package:news_board/presentation/pages/detail_page.dart';

class NewsBoardApp extends StatelessWidget {
  const NewsBoardApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: '新闻看板',
      theme: AppTheme.darkTheme,
      debugShowCheckedModeBanner: false,
      initialRoute: '/',
      routes: {
        '/': (context) => const HomePage(),
        '/detail': (context) => const DetailPage(),
      },
    );
  }
}
```

---

## 第七阶段：Android 配置与打包

### 7.1 Android 配置检查

确保 `android/app/build.gradle` 配置正确：

```gradle
plugins {
    id "com.android.application"
    id "kotlin-android"
    id "dev.flutter.flutter-gradle-plugin"
}

android {
    namespace = "com.example.news_board"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.example.news_board"
        minSdk = 21
        targetSdk = 34
        versionCode = 1
        versionName = "1.0"
    }

    buildTypes {
        release {
            signingConfig = signingConfigs.debug
        }
    }
}

flutter {
    source = "../.."
}
```

### 7.2 打包 APK

```bash
cd 新闻采集
flutter build apk --debug
# 或发布版本
flutter build apk --release
```

### 7.3 验证 APK

```bash
# 检查生成的 APK
ls -la build/app/outputs/flutter-apk/
```

---

## 开发流程检查清单

### 每一步完成后，AI 助手应确认：

- [ ] 代码语法正确，无编译错误
- [ ] 相关依赖已添加到 `pubspec.yaml`
- [ ] 执行了 `flutter pub get`
- [ ] 遵循 Clean Architecture 分层
- [ ] 变量/函数命名清晰，符合规范
- [ ] 关键逻辑有注释说明

### 遇到问题时的处理流程：

1. **先自行排查**：检查代码、配置、依赖是否正确
2. **查阅文档**：Flutter 官方文档、Dart 文档
3. **搜索解决方案**：使用搜索引擎查找类似问题
4. **向用户报告**：如无法解决，说明问题及已尝试的方法

---

## 常用命令参考

```bash
# 项目创建与依赖
flutter create news_board
cd news_board && flutter pub get

# 代码检查
flutter analyze

# 热重载开发
flutter run

# APK 打包
flutter build apk --debug
flutter build apk --release

# 清理与重建
flutter clean
flutter pub get

# 查看设备
flutter devices
```

---

## 相关文档

- [Flutter 设计规格](./flutter-design.md)
- [前端设计规格](./frontend-design.md)