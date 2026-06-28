import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../data/models/news_item.dart';
import '../../core/providers/auth_provider.dart';
import 'news_card_content.dart';
import 'lock_overlay.dart';
import 'news_detail_dialog.dart';

/// 新闻卡片（主 shell）
class NewsCard extends ConsumerWidget {
  final NewsItem news;
  final bool isLocked;
  final String lockTitle;
  final String lockButtonLoggedIn;
  final String lockButtonNotLoggedIn;

  const NewsCard({
    super.key,
    required this.news,
    this.isLocked = false,
    this.lockTitle = '订阅后可查看完整内容',
    this.lockButtonLoggedIn = '立即订阅',
    this.lockButtonNotLoggedIn = '登录后订阅',
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final authState = ref.watch(authProvider);
    final hasAccess = ref.watch(hasSubscriptionAccessProvider);
    // 使用统一方法判断：isLocked 且 用户无订阅访问权限时显示锁
    final showLock = isLocked && !hasAccess;

    return Stack(
      children: [
        NewsCardContent(
          news: news,
          isLocked: showLock,
          onTap: showLock ? null : () => _showDetail(context),
        ),
        if (showLock)
          LockOverlay(
            isLoggedIn: authState.isLoggedIn,
            lockTitle: lockTitle,
            lockButtonLoggedIn: lockButtonLoggedIn,
            lockButtonNotLoggedIn: lockButtonNotLoggedIn,
          ),
      ],
    );
  }

  void _showDetail(BuildContext context) {
    showGeneralDialog(
      context: context,
      barrierDismissible: true,
      barrierLabel: '关闭',
      barrierColor: Colors.black87,
      transitionDuration: const Duration(milliseconds: 300),
      pageBuilder: (context, _, __) => NewsDetailDialog(news: news),
    );
  }
}