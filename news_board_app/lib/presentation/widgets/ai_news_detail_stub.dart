import 'dart:html' as html;
import 'dart:ui_web' as ui_web;
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import '../../data/models/news_item.dart';

/// AI 新闻详情弹窗
/// - Android: WebView 内嵌（实际类在 ai_news_detail_dialog.dart）
/// - Web: iframe 内嵌（本文件通过 kIsWeb 运行时切换）
class AiNewsDetailDialog extends StatelessWidget {
  final AiNewsItem news;
  const AiNewsDetailDialog({super.key, required this.news});

  @override
  Widget build(BuildContext context) {
    if (kIsWeb) {
      return _WebAiDetail(news: news);
    }
    // Android: should not reach here on web, actual dialog loaded via conditional import
    return const SizedBox();
  }
}

// ignore: avoid_web_libraries
class _WebAiDetail extends StatefulWidget {
  final AiNewsItem news;
  const _WebAiDetail({required this.news});
  @override
  State<_WebAiDetail> createState() => _WebAiDetailState();
}

class _WebAiDetailState extends State<_WebAiDetail> {
  late final String _viewType;

  @override
  void initState() {
    super.initState();
    _viewType = 'web-iframe-${widget.news.url.hashCode}';
    _registerIframe();
  }

  void _registerIframe() {
    // ignore: undefined_prefixed_name
    ui_web.platformViewRegistry.registerViewFactory(_viewType, (int viewId) {
      final iframe = html.IFrameElement()
        ..src = widget.news.url
        ..style.border = 'none'
        ..style.width = '100%'
        ..style.height = '100%'
        ..style.display = 'block';
      return iframe;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.transparent,
      body: Stack(
        children: [
          Positioned.fill(child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: HtmlElementView(viewType: _viewType),
          )),
          Positioned(
            top: MediaQuery.of(context).padding.top + 8,
            right: 16,
            child: Material(
              color: Colors.grey[800],
              shape: const CircleBorder(),
              child: InkWell(
                onTap: () => Navigator.pop(context),
                customBorder: const CircleBorder(),
                child: const Padding(
                  padding: EdgeInsets.all(10),
                  child: Icon(Icons.close, color: Colors.white, size: 22),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
