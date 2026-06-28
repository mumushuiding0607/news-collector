import 'package:flutter/material.dart';

/// 卡片底部：来源 + 时间
class NewsCardFooter extends StatelessWidget {
  final String sourceName;
  final String publishTime;

  const NewsCardFooter({
    super.key,
    required this.sourceName,
    required this.publishTime,
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        _buildSourceTag(),
        const Spacer(),
        const Icon(Icons.access_time, size: 12, color: Colors.white38),
        const SizedBox(width: 4),
        Text(_formatTime(publishTime), style: const TextStyle(color: Colors.white38, fontSize: 12)),
      ],
    );
  }

  Widget _buildSourceTag() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.08),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Text(sourceName, style: const TextStyle(color: Colors.white54, fontSize: 12)),
    );
  }

  String _formatTime(String timeStr) {
    if (timeStr.isEmpty) return '';
    try {
      final parts = timeStr.split(' ');
      if (parts.length >= 2) {
        return '${parts[0]} ${parts[1].substring(0, 5)}';
      }
      return timeStr;
    } catch (_) {
      return timeStr;
    }
  }
}
