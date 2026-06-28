import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'core/providers/config_provider.dart' show ApiConfig, configProvider, ThemeConfig;
import 'core/providers/version_provider.dart';
import 'core/router/app_router.dart';
import 'core/providers/subscription_provider.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  SystemChrome.setSystemUIOverlayStyle(const SystemUiOverlayStyle(
    statusBarColor: Colors.transparent,
    statusBarIconBrightness: Brightness.light,
    systemNavigationBarColor: Colors.transparent,
    systemNavigationBarIconBrightness: Brightness.light,
  ));

  // 在 runApp 前加载 API 配置，确保任何请求发出前配置已就绪
  await ApiConfig.loadFromConfig();

  runApp(const ProviderScope(child: NewsBoardApp()));
}

class NewsBoardApp extends ConsumerStatefulWidget {
  const NewsBoardApp({super.key});

  @override
  ConsumerState<NewsBoardApp> createState() => _NewsBoardAppState();
}

class _NewsBoardAppState extends ConsumerState<NewsBoardApp> with WidgetsBindingObserver {
  bool _initialized = false;
  bool _updateChecked = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    Future.microtask(() => _initialize());
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    // 当应用从后台恢复时，刷新配置（确保获取最新的订阅功能开关等配置）
    if (state == AppLifecycleState.resumed) {
      ref.read(configProvider.notifier).refresh();
    }
  }

  Future<void> _initialize() async {
    // API 配置已在 main() 中通过 await 加载，此处只加载应用配置
    await ref.read(configProvider.notifier).load();

    // 配置加载完成后检查更新
    if (!_updateChecked) {
      _updateChecked = true;
      await ref.read(versionProvider.notifier).checkForUpdate();
    }
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (!_initialized) {
      _initialized = true;
      final config = ref.read(configProvider);
      if (config.subscriptionTiers.isNotEmpty) {
        ref.read(subscriptionProvider.notifier).setPlansFromConfig(config.subscriptionTiers);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final config = ref.watch(configProvider);
    final theme = config.theme;

    // 监听版本检查结果，弹出更新提示（延迟10秒确保UI已就绪）
    ref.listen<VersionCheckResult>(versionProvider, (prev, next) {
      if (next.status == VersionCheckStatus.updateAvailable && next.config != null) {
        final ctx = context;
        Future.delayed(const Duration(seconds: 10), () {
          if (mounted) {
            showUpdateDialogIfNeeded(ctx, ref);
          }
        });
      }
    });

    return MaterialApp.router(
      title: config.appName,
      debugShowCheckedModeBanner: false,
      theme: _buildTheme(theme),
      routerConfig: appRouter,
    );
  }

  ThemeData _buildTheme(ThemeConfig theme) {
    return ThemeData(
      brightness: Brightness.dark,
      scaffoldBackgroundColor: theme.backgroundStartColor,
      primaryColor: theme.accentRedColor,
      appBarTheme: AppBarTheme(
        backgroundColor: Colors.transparent,
        elevation: 0,
        centerTitle: true,
        titleTextStyle: TextStyle(
          color: theme.textPrimaryColor,
          fontSize: 20,
          fontWeight: FontWeight.bold,
        ),
        iconTheme: IconThemeData(color: theme.textPrimaryColor),
      ),
      colorScheme: ColorScheme.dark(
        primary: theme.accentRedColor,
        secondary: theme.accentGoldColor,
        surface: theme.backgroundStartColor,
        onPrimary: Colors.white,
        onSecondary: Colors.black,
        onSurface: theme.textPrimaryColor,
      ),
      textTheme: TextTheme(
        headlineLarge: TextStyle(
          color: theme.textPrimaryColor,
          fontSize: 28,
          fontWeight: FontWeight.bold,
        ),
        headlineMedium: TextStyle(
          color: theme.textPrimaryColor,
          fontSize: 22,
          fontWeight: FontWeight.bold,
        ),
        titleLarge: TextStyle(
          color: theme.textPrimaryColor,
          fontSize: 18,
          fontWeight: FontWeight.w600,
        ),
        titleMedium: TextStyle(
          color: theme.textPrimaryColor,
          fontSize: 16,
          fontWeight: FontWeight.w500,
        ),
        bodyLarge: TextStyle(
          color: theme.textPrimaryColor,
          fontSize: 16,
        ),
        bodyMedium: TextStyle(
          color: theme.textSecondaryColor,
          fontSize: 14,
        ),
        bodySmall: TextStyle(
          color: theme.textMutedColor,
          fontSize: 12,
        ),
      ),
    );
  }
}