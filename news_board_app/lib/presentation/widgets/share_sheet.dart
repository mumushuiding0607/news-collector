import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:share_plus/share_plus.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:path_provider/path_provider.dart';
import 'dart:io';
import '../../core/providers/config_provider.dart';
import '../../data/models/news_item.dart';

/// 分享图片弹窗（只负责显示图片和分享）
class ShareSheet extends ConsumerWidget {
  final NewsItem news;
  final Uint8List imageBytes;

  const ShareSheet({super.key, required this.news, required this.imageBytes});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final config = ref.watch(configProvider);
    final channels = config.download.enabledChannels;

    return Scaffold(
      backgroundColor: const Color(0xFF1A1A1A),
      body: SafeArea(
        child: Column(
          children: [
            // 标题栏
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  IconButton(
                    onPressed: () => Navigator.pop(context),
                    icon: const Icon(Icons.close, color: Colors.white54),
                  ),
                  const Text(
                    '分享到',
                    style: TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(width: 48),
                ],
              ),
            ),
            // 显示图片（可滚动查看）
            Expanded(
              child: SingleChildScrollView(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(12),
                  child: Image.memory(
                    imageBytes,
                    fit: BoxFit.contain,
                    width: double.infinity,
                  ),
                ),
              ),
            ),
            // 下载渠道
            if (channels.isNotEmpty)
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                child: Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: Colors.white.withValues(alpha: 0.05),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                    children: channels.map((channel) => _DownloadButton(channel: channel)).toList(),
                  ),
                ),
              ),
            // 分享按钮栏
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
              decoration: BoxDecoration(
                color: Colors.black.withValues(alpha: 0.3),
                border: Border(top: BorderSide(color: Colors.white.withValues(alpha: 0.1))),
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                children: [
                  _SharePlatformButton(
                    icon: Icons.chat,
                    label: '微信',
                    color: const Color(0xFF07C160),
                    onTap: () => _shareImage(context, news.title, imageBytes),
                  ),
                  _SharePlatformButton(
                    icon: Icons.group,
                    label: '朋友圈',
                    color: const Color(0xFF07C160),
                    onTap: () => _shareImage(context, news.title, imageBytes),
                  ),
                  if (!kIsWeb)
                    _SharePlatformButton(
                      icon: Icons.share,
                      label: '更多',
                      color: const Color(0xFFFF9500),
                      onTap: () => _shareImage(context, news.title, imageBytes),
                    ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  /// 显示分享弹窗（传入已生成的图片字节）
  static Future<void> showWithImage(BuildContext context, NewsItem news, Uint8List imageBytes) {
    return showGeneralDialog(
      context: context,
      barrierDismissible: true,
      barrierLabel: '关闭',
      barrierColor: Colors.black87,
      transitionDuration: const Duration(milliseconds: 300),
      pageBuilder: (_, _, _) => ShareSheet(news: news, imageBytes: imageBytes),
    );
  }

  /// 分享图片到各平台
  static Future<void> _shareImage(BuildContext context, String text, Uint8List imageBytes) async {
    try {
      final XFile file;
      if (kIsWeb) {
        // Web 平台：直接通过字节数据创建 XFile（无需写入磁盘）
        file = XFile.fromData(
          imageBytes,
          name: 'share.png',
          mimeType: 'image/png',
        );
      } else {
        // 移动/桌面平台：写入临时文件
        final directory = await getTemporaryDirectory();
        final filePath = '${directory.path}/share_${DateTime.now().millisecondsSinceEpoch}.png';
        final tempFile = File(filePath);
        await tempFile.writeAsBytes(imageBytes);
        file = XFile(filePath, mimeType: 'image/png');
      }

      await SharePlus.instance.share(ShareParams(
        text: text,
        files: [file],
      ));
    } catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('分享失败: $e')),
        );
      }
    }
  }
}

/// 分享平台按钮
class _SharePlatformButton extends StatelessWidget {
  final IconData icon;
  final String label;
  final Color color;
  final VoidCallback onTap;

  const _SharePlatformButton({
    required this.icon,
    required this.label,
    required this.color,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Column(
        children: [
          Container(
            width: 48,
            height: 48,
            decoration: BoxDecoration(
              color: color.withValues(alpha: 0.15),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Icon(icon, color: color, size: 24),
          ),
          const SizedBox(height: 4),
          Text(label, style: const TextStyle(color: Colors.white70, fontSize: 11)),
        ],
      ),
    );
  }
}

/// 下载渠道按钮
class _DownloadButton extends ConsumerWidget {
  final DownloadChannel channel;

  const _DownloadButton({required this.channel});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return GestureDetector(
      onTap: () => _openDownload(context),
      child: Column(
        children: [
          Container(
            width: 40,
            height: 40,
            decoration: BoxDecoration(
              color: _getChannelColor(channel.icon).withValues(alpha: 0.2),
              borderRadius: BorderRadius.circular(10),
            ),
            child: Icon(_getChannelIcon(channel.icon), color: _getChannelColor(channel.icon), size: 20),
          ),
          const SizedBox(height: 2),
          Text(channel.name, style: const TextStyle(color: Colors.white54, fontSize: 9)),
        ],
      ),
    );
  }

  IconData _getChannelIcon(String icon) {
    switch (icon) {
      case 'huawei':
        return Icons.cloud_download;
      default:
        return Icons.download_rounded;
    }
  }

  Color _getChannelColor(String icon) {
    switch (icon) {
      case 'huawei':
        return Colors.red.shade400;
      default:
        return Colors.amber;
    }
  }

  Future<void> _openDownload(BuildContext context) async {
    if (channel.url.isEmpty) return;

    final uri = Uri.parse(channel.url);
    try {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    } catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('打开失败: $e')),
        );
      }
    }
  }
}
