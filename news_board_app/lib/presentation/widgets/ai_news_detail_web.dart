import 'dart:html' as html;
import 'package:flutter/material.dart';
import '../../data/models/news_item.dart';

class AiNewsDetailDialog extends StatefulWidget {
  final AiNewsItem news;
  const AiNewsDetailDialog({super.key, required this.news});
  @override
  State<AiNewsDetailDialog> createState() => _AiNewsDetailDialogState();
}

class _AiNewsDetailDialogState extends State<AiNewsDetailDialog> {
  @override
  void initState() {
    super.initState();
    html.window.open(widget.news.url, '_blank');
    Navigator.pop(context);
  }

  @override
  Widget build(BuildContext context) {
    return const Scaffold(body: Center(child: CircularProgressIndicator()));
  }
}
