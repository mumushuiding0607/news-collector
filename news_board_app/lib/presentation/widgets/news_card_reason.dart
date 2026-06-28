import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/providers/config_provider.dart';

/// 推荐逻辑预览
class NewsCardReason extends ConsumerWidget {
  final String reason;

  const NewsCardReason({super.key, required this.reason});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = ref.watch(configProvider).theme;

    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: theme.accentGoldColor.withOpacity(0.08),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: theme.accentGoldColor.withOpacity(0.2)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.lightbulb_outline, color: theme.accentGoldColor, size: 14),
              const SizedBox(width: 6),
              Text(
                '推荐逻辑',
                style: TextStyle(
                  color: theme.accentGoldColor,
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            reason,
            style: const TextStyle(color: Colors.white60, fontSize: 13, height: 1.4),
            maxLines: 3,
            overflow: TextOverflow.ellipsis,
          ),
        ],
      ),
    );
  }
}
