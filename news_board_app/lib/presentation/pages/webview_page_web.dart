// ignore_for_file: avoid_web_libraries
import 'dart:html' as html;
import 'dart:ui_web' as ui_web;

import 'package:flutter/material.dart';

/// Web 平台实现：使用 iframe 嵌入目标网页
class WebViewPage extends StatefulWidget {
  final String url;
  final String title;

  const WebViewPage({super.key, required this.url, this.title = '网页'});

  @override
  State<WebViewPage> createState() => _WebViewPageState();
}

class _WebViewPageState extends State<WebViewPage> {
  late final String _viewType;
  bool _registered = false;

  @override
  void initState() {
    super.initState();
    _viewType = 'iframe-view-${widget.url.hashCode}';
    _registerIframe();
  }

  void _registerIframe() {
    if (_registered) return;
    _registered = true;
    ui_web.platformViewRegistry.registerViewFactory(
      _viewType,
      (int viewId) {
        final iframe = html.IFrameElement()
          ..src = widget.url
          ..style.border = 'none'
          ..style.width = '100%'
          ..style.height = '100%'
          ..style.display = 'block';
        return iframe;
      },
    );
  }

  @override
  void didUpdateWidget(WebViewPage oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.url != widget.url) {
      _registered = false;
      _registerIframe();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.title, style: const TextStyle(fontSize: 16)),
        backgroundColor: const Color(0xFF1E1E1E),
        foregroundColor: Colors.white,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.close),
          onPressed: () => Navigator.pop(context),
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () {
              // 刷新 iframe：重新注册以加载新 URL
              setState(() {
                _registered = false;
                _registerIframe();
              });
            },
          ),
        ],
      ),
      body: HtmlElementView(viewType: _viewType),
    );
  }
}
