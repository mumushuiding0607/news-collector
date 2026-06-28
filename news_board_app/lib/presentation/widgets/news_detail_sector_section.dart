import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/providers/config_provider.dart';
import '../../data/models/news_item.dart';

/// 详情页-板块涨跌区块（展示当前涨跌幅 + 发布以来涨跌幅）
class NewsDetailSectorSection extends ConsumerWidget {
  final List<String> sectors;
  final List<double> currentChangeRates;
  final List<SectorChange> sectorChanges;

  const NewsDetailSectorSection({
    super.key,
    required this.sectors,
    required this.currentChangeRates,
    required this.sectorChanges,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = ref.watch(configProvider).theme;
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.05),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('板块涨跌', style: TextStyle(color: theme.textMutedColor, fontSize: 12)),
          const SizedBox(height: 12),
          ...sectors.asMap().entries.map((e) => _buildRow(theme, e.key, e.value)),
        ],
      ),
    );
  }

  Widget _buildRow(ThemeConfig theme, int index, String sector) {
    final double currentRate = index < currentChangeRates.length ? currentChangeRates[index] : 0.0;
    final change = _getChange(sector);
    final publishPct = change.publishValue > 0 ? (change.change / change.publishValue * 100) : 0.0;
    final isPublishPositive = publishPct >= 0;
    final publishColor = isPublishPositive ? theme.accentRedColor : theme.accentGreenColor;

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        children: [
          Text(sector, style: const TextStyle(color: Colors.white70, fontSize: 14)),
          const SizedBox(width: 12),
          // 当前涨跌幅
          _buildRateChip(
            currentRate >= 0 ? theme.accentRedColor : theme.accentGreenColor,
            '当前',
            currentRate,
          ),
          const SizedBox(width: 8),
          // 发布以来涨跌幅
          _buildRateChip(
            publishColor,
            '发布来',
            publishPct,
          ),
        ],
      ),
    );
  }

  Widget _buildRateChip(Color color, String label, double rate) {
    final isPositive = rate >= 0;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: color.withOpacity(0.15),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: color.withOpacity(0.3)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(label, style: TextStyle(color: color.withOpacity(0.7), fontSize: 10)),
          const SizedBox(width: 2),
          Icon(isPositive ? Icons.arrow_upward : Icons.arrow_downward, color: color, size: 12),
          Text(
            '${rate.abs().toStringAsFixed(1)}%',
            style: TextStyle(color: color, fontSize: 12, fontWeight: FontWeight.bold),
          ),
        ],
      ),
    );
  }

  SectorChange _getChange(String sector) {
    return sectorChanges.firstWhere(
      (c) => c.name == sector,
      orElse: () => SectorChange(
        name: sector,
        publishValue: 0,
        currentValue: 0,
        change: 0,
      ),
    );
  }
}