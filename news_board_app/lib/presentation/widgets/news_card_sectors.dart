import 'package:flutter/material.dart';
import '../../core/theme/app_theme.dart';
import '../../data/models/news_item.dart';

/// 板块涨跌标签
class NewsCardSectors extends StatelessWidget {
  final List<String> sectors;
  final List<SectorChange> sectorChanges;

  const NewsCardSectors({
    super.key,
    required this.sectors,
    required this.sectorChanges,
  });

  @override
  Widget build(BuildContext context) {
    if (sectors.isEmpty) return const SizedBox.shrink();

    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: sectors.map((s) => _buildTag(context, s)).toList(),
    );
  }

  Widget _buildTag(BuildContext context, String sector) {
    final change = _getChange(sector);
    final isPositive = change.change >= 0;
    final color = isPositive ? AppTheme.accentRed : AppTheme.accentGreen;
    final glassBg = isPositive ? AppTheme.glassRed : AppTheme.accentGreen.withOpacity(0.1);
    final glassBorder = isPositive ? AppTheme.glassRedBorder : AppTheme.accentGreen.withOpacity(0.3);
    final pct = _calcPct(change);

    return Tooltip(
      message: '消息发布以来涨幅',
      textStyle: const TextStyle(color: Colors.white70, fontSize: 12),
      decoration: BoxDecoration(
        color: Colors.grey.shade800,
        borderRadius: BorderRadius.circular(8),
      ),
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        decoration: BoxDecoration(
          color: glassBg,
          borderRadius: BorderRadius.circular(18),
          border: Border.all(color: glassBorder),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(sector, style: const TextStyle(color: Colors.white70, fontSize: 13)),
            const SizedBox(width: 4),
            Icon(isPositive ? Icons.arrow_upward : Icons.arrow_downward, color: color, size: 16),
            Text('${pct.abs().toStringAsFixed(2)}%', style: TextStyle(color: color, fontSize: 14, fontWeight: FontWeight.bold)),
          ],
        ),
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

  double _calcPct(SectorChange change) {
    return change.publishValue > 0 ? (change.change / change.publishValue * 100) : 0.0;
  }
}