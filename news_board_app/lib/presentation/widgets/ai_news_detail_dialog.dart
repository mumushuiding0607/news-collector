import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../data/models/news_item.dart';

// Conditional import: webview_stub for web, webview_page for mobile
import '../pages/webview_stub.dart'
    if (dart.library.io) '../pages/webview_page.dart';

/// AI 新闻详情弹窗（全屏 WebView）
class AiNewsDetailDialog extends ConsumerWidget {
  final AiNewsItem news;

  const AiNewsDetailDialog({super.key, required this.news});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Scaffold(
      backgroundColor: Colors.transparent,
      body: Stack(
        children: [
          // 全屏 WebView
          WebViewPage(
            url: news.url,
            title: '',
          ),
          // 关闭按钮
          Positioned(
            top: MediaQuery.of(context).padding.top + 8,
            right: 8,
            child: GestureDetector(
              onTap: () => Navigator.pop(context),
              child: Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: Colors.black54,
                  borderRadius: BorderRadius.circular(20),
                ),
                child: const Icon(Icons.close, color: Colors.white, size: 22),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
