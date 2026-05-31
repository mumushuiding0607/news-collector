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

  const NewsCard({super.key, required this.news, this.isLocked = false});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final authState = ref.watch(authProvider);
    final showLock = isLocked && authState.subscriptionLevel == 'free';

    return Stack(
      children: [
        NewsCardContent(
          news: news,
          isLocked: showLock,
          onTap: showLock ? null : () => _showDetail(context),
        ),
        if (showLock) LockOverlay(isLoggedIn: authState.isLoggedIn),
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