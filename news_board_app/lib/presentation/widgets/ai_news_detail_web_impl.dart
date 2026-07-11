import 'dart:html' as html;
import 'dart:ui_web' as ui_web;
import 'package:flutter/material.dart';
import '../../data/models/news_item.dart';

/// AI 新闻详情 - Web 实现（iframe 内嵌，不跳出标签页）
class AiNewsDetailWebImpl extends StatefulWidget {
  final AiNewsItem news;
  const AiNewsDetailWebImpl({super.key, required this.news});
  @override
  State<AiNewsDetailWebImpl> createState() => _AiNewsDetailWebImplState();
}

class _AiNewsDetailWebImplState extends State<AiNewsDetailWebImpl> {
  late final String _viewType;

  @override
  void initState() {
    super.initState();
    _viewType = 'web-iframe-${widget.news.url.hashCode}';
    _registerIframe();
  }

  void _registerIframe() {
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
          Positioned.fill(child: HtmlElementView(viewType: _viewType)),
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
