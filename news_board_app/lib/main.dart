import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'core/theme/app_theme.dart';
import 'core/router/app_router.dart';
import 'core/providers/config_provider.dart';
import 'core/providers/subscription_provider.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();

  SystemChrome.setSystemUIOverlayStyle(const SystemUiOverlayStyle(
    statusBarColor: Colors.transparent,
    statusBarIconBrightness: Brightness.light,
    systemNavigationBarColor: Colors.transparent,
    systemNavigationBarIconBrightness: Brightness.light,
  ));

  runApp(const ProviderScope(child: NewsBoardApp()));
}

class NewsBoardApp extends ConsumerStatefulWidget {
  const NewsBoardApp({super.key});

  @override
  ConsumerState<NewsBoardApp> createState() => _NewsBoardAppState();
}

class _NewsBoardAppState extends ConsumerState<NewsBoardApp> {
  @override
  void initState() {
    super.initState();
    // 启动时加载配置
    Future.microtask(() {
      ref.read(configProvider.notifier).load();
      // 配置加载后，同步套餐到订阅 provider
      ref.listen(configProvider, (prev, next) {
        if (next.subscriptionTiers.isNotEmpty) {
          ref.read(subscriptionProvider.notifier).setPlansFromConfig(next.subscriptionTiers);
        }
      });
    });
  }

  @override
  Widget build(BuildContext context) {
    final config = ref.watch(configProvider);

    return MaterialApp.router(
      title: config.appName,
      debugShowCheckedModeBanner: false,
      theme: AppTheme.darkTheme,
      routerConfig: appRouter,
    );
  }
}