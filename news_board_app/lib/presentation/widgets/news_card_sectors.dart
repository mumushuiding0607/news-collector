import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/providers/config_provider.dart';
import '../../data/models/news_item.dart';

/// 板块涨跌标签（用于新闻列表页，展示当前涨跌幅）
class NewsCardSectors extends ConsumerWidget {
  final List<String> sectors;
  final Map<String, double> currentChangeRates;

  const NewsCardSectors({
    super.key,
    required this.sectors,
    required this.currentChangeRates,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = ref.watch(configProvider).theme;
    if (sectors.isEmpty) return const SizedBox.shrink();

    return Wrap(
      spacing: 6,
      runSpacing: 6,
      children: sectors.map((s) => _buildTag(theme, s)).toList(),
    );
  }

  Widget _buildTag(ThemeConfig theme, String sector) {
    final rate = currentChangeRates[sector] ?? 0;
    final isPositive = rate >= 0;
    final color = isPositive ? theme.accentRedColor : theme.accentGreenColor;
    final glassBg = isPositive ? theme.glassRedColor : theme.accentGreenColor.withOpacity(0.1);
    final glassBorder = isPositive ? theme.glassRedBorderColor : theme.accentGreenColor.withOpacity(0.3);

    return Tooltip(
      message: '当前涨跌幅',
      textStyle: const TextStyle(color: Colors.white70, fontSize: 12),
      decoration: BoxDecoration(
        color: Colors.grey.shade800,
        borderRadius: BorderRadius.circular(8),
      ),
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
        decoration: BoxDecoration(
          color: glassBg,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: glassBorder),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(sector, style: const TextStyle(color: Colors.white70, fontSize: 12)),
            const SizedBox(width: 2),
            Icon(isPositive ? Icons.arrow_upward : Icons.arrow_downward, color: color, size: 14),
            Text('${rate.abs().toStringAsFixed(1)}%', style: TextStyle(color: color, fontSize: 13, fontWeight: FontWeight.bold)),
          ],
        ),
      ),
    );
  }
}