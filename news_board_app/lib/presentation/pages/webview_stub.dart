// Stub for web platform - webview_flutter doesn't support web
import 'package:flutter/material.dart';

class WebViewPage extends StatelessWidget {
  final String url;
  final String title;
  const WebViewPage({super.key, required this.url, this.title = '网页'});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(title)),
      body: const Center(child: Text('WebView 不支持 Web 平台')),
    );
  }
}
