import 'package:flutter/material.dart';
import '../../core/theme/app_theme.dart';
import '../../data/models/news_item.dart';

/// 详情页-板块涨跌区块
class NewsDetailSectorSection extends StatelessWidget {
  final List<String> sectors;
  final List<SectorChange> sectorChanges;

  const NewsDetailSectorSection({
    super.key,
    required this.sectors,
    required this.sectorChanges,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.05),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('板块涨跌（发布以来）', style: TextStyle(color: Colors.white54, fontSize: 12)),
          const SizedBox(height: 12),
          ...sectors.map((s) => _buildRow(context, s)),
        ],
      ),
    );
  }

  Widget _buildRow(BuildContext context, String sector) {
    final change = _getChange(sector);
    final isPositive = change.change >= 0;
    final color = isPositive ? AppTheme.accentRed : AppTheme.accentGreen;
    final pct = _calcPct(change);

    return Tooltip(
      message: '消息发布至今涨幅',
      textStyle: const TextStyle(color: Colors.white70, fontSize: 12),
      decoration: BoxDecoration(
        color: Colors.grey.shade800,
        borderRadius: BorderRadius.circular(8),
      ),
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 6),
        child: Row(
          children: [
            Text(sector, style: const TextStyle(color: Colors.white70, fontSize: 14)),
            const Spacer(),
            Icon(
              isPositive ? Icons.arrow_upward : Icons.arrow_downward,
              color: color,
              size: 18,
            ),
            const SizedBox(width: 4),
            Text(
              '${pct.abs().toStringAsFixed(2)}%',
              style: TextStyle(color: color, fontSize: 16, fontWeight: FontWeight.bold),
            ),
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