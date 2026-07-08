import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../presentation/pages/news_list_page.dart';
import '../../presentation/pages/login_page.dart';
import '../../presentation/pages/register_page.dart';
import '../../presentation/pages/subscription_page.dart';
import '../../presentation/pages/account_page.dart';
import '../../presentation/pages/download_page.dart';
import '../../presentation/pages/webview_page.dart';
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
    GoRoute(
      path: '/webview',
      builder: (context, state) {
        final url = state.uri.queryParameters['url'] ?? '';
        final title = state.uri.queryParameters['title'] ?? '网页';
        return WebViewPage(url: url, title: title);
      },
    ),
  ],
);
