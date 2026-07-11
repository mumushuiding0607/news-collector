import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';
import '../../data/models/news_item.dart';

/// AI 新闻详情 - Web 专用（无 Android 依赖）
/// Web 端直接打开浏览器，不需要弹窗
class AiNewsDetailWebOnly {
  static Future<void> open(AiNewsItem news) async {
    final uri = Uri.parse(news.url);
    if (await canLaunchUrl(uri)) {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    }
  }
}
