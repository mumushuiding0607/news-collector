import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../presentation/pages/news_list_page.dart';
import '../../presentation/pages/login_page.dart';
import '../../presentation/pages/register_page.dart';
import '../../presentation/pages/subscription_page.dart';
import '../../presentation/pages/account_page.dart';
import '../../presentation/pages/download_page.dart';
import '../utils/api_client.dart';

final appRouter = GoRouter(
  navigatorKey: ApiClient.rootNavigatorKey,
  initialLocation: '/',
  routes: [
    GoRoute(
      path: '/',
      builder: (context, state) => const NewsListPage(),
    ),
    GoRoute(
      path: '/login',
      builder: (context, state) => const LoginPage(),
    ),
    GoRoute(
      path: '/register',
      builder: (context, state) => const RegisterPage(),
    ),
    GoRoute(
      path: '/subscribe',
      builder: (context, state) => const SubscriptionPage(),
    ),
    GoRoute(
      path: '/account',
      builder: (context, state) => const AccountPage(),
    ),
    GoRoute(
      path: '/download',
      builder: (context, state) => const DownloadPage(),
    ),
  ],
);

/// 路由映射表
final _routeMap = <String, Widget Function()>{
  '/': () => const NewsListPage(),
  '/login': () => const LoginPage(),
  '/register': () => const RegisterPage(),
  '/subscribe': () => const SubscriptionPage(),
  '/account': () => const AccountPage(),
  '/download': () => const DownloadPage(),
};

/// 根据路由设置生成页面
Route<dynamic>? generateRoute(RouteSettings settings) {
  final name = settings.name ?? '/';
  final builder = _routeMap[name];
  if (builder != null) {
    return MaterialPageRoute(builder: (_) => builder());
  }
  // 未知路由返回 404
   return MaterialPageRoute(
    builder: (ctx) => Scaffold(
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Text('404', style: TextStyle(fontSize: 48, fontWeight: FontWeight.bold)),
            const SizedBox(height: 16),
            const Text('页面不存在', style: TextStyle(fontSize: 18)),
            const SizedBox(height: 24),
            ElevatedButton(
              onPressed: () => Navigator.of(ctx).pushAndRemoveUntil(
                MaterialPageRoute(builder: (_) => const NewsListPage()),
                (_) => false,
              ),
              child: const Text('返回首页'),
            ),
          ],
        ),
      ),
    ),
  );
}