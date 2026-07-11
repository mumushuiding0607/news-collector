import 'package:flutter/material.dart';
import 'package:webview_flutter/webview_flutter.dart';
import '../../data/models/news_item.dart';

/// AI 新闻详情 - Android 实现（WebView 嵌入）
class AiNewsDetailDialogImpl extends StatefulWidget {
  final AiNewsItem news;

  const AiNewsDetailDialogImpl({super.key, required this.news});

  @override
  State<AiNewsDetailDialogImpl> createState() => _AiNewsDetailDialogImplState();
}

class _AiNewsDetailDialogImplState extends State<AiNewsDetailDialogImpl> {
  late final WebViewController _controller;
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _controller = WebViewController()
      ..setJavaScriptMode(JavaScriptMode.unrestricted)
      ..setNavigationDelegate(
        NavigationDelegate(
          onPageStarted: (_) => setState(() => _isLoading = true),
          onPageFinished: (_) => setState(() => _isLoading = false),
          onWebResourceError: (e) => debugPrint('WebView error: ${e.description}'),
        ),
      )
      ..loadRequest(Uri.parse(widget.news.url));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.transparent,
      body: Stack(
        children: [
          WebViewWidget(controller: _controller),
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
          if (_isLoading)
            const Center(child: CircularProgressIndicator()),
        ],
      ),
    );
  }
}
