import 'package:flutter/material.dart';
import '../../data/models/news_item.dart';
import '../../shared/widgets/score_badge.dart';

/// 新闻卡片主体内容
class NewsCardContent extends StatelessWidget {
  final NewsItem news;
  final bool isLocked;
  final VoidCallback? onTap;

  const NewsCardContent({
    super.key,
    required this.news,
    this.isLocked = false,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [Color(0x22E53935), Color(0x11E53935)],
        ),
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: Colors.white.withOpacity(0.18), width: 1),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.25),
            blurRadius: 20,
            offset: const Offset(0, 8),
          ),
        ],
      ),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(24),
          splashColor: Colors.white.withOpacity(0.1),
          highlightColor: Colors.white.withOpacity(0.05),
          child: Padding(
            padding: const EdgeInsets.all(18),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _buildHeader(),
                if (news.sectorList.isNotEmpty) ...[
                  const SizedBox(height: 14),
                  _buildSectors(),
                ],
                if (news.reason.isNotEmpty) ...[
                  const SizedBox(height: 12),
                  _buildReason(),
                ],
                if (news.coreStocksPreview.isNotEmpty) ...[
                  const SizedBox(height: 12),
                  _buildStocks(),
                ],
                const SizedBox(height: 12),
                _buildFooter(),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildHeader() {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Expanded(
          child: Opacity(
            opacity: isLocked ? 0.65 : 1.0,
            child: Text(
              news.title,
              style: const TextStyle(
                color: Colors.white,
                fontSize: 17,
                fontWeight: FontWeight.bold,
                height: 1.3,
              ),
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
          ),
        ),
        const SizedBox(width: 12),
        ScoreBadge(score: news.importanceScore, size: 42, isLocked: isLocked),
      ],
    );
  }

  Widget _buildSectors() {
    return Opacity(
      opacity: isLocked ? 0.65 : 1.0,
      child: Wrap(
        spacing: 8,
        runSpacing: 8,
        children: news.sectorList.map((s) => _buildSectorTag(s)).toList(),
      ),
    );
  }

  Widget _buildSectorTag(String sector) {
    final change = _getChange(sector);
    final isPositive = change.change >= 0;
    final color = isPositive ? const Color(0xFFE53935) : const Color(0xFF43A047);
    final pct = _calcPct(change);

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: color.withOpacity(0.15),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: color.withOpacity(0.3)),
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
    );
  }

  Widget _buildReason() {
    return Opacity(
      opacity: isLocked ? 0.65 : 1.0,
      child: Text(
        news.reason,
        style: const TextStyle(color: Colors.white54, fontSize: 13, height: 1.4),
        maxLines: 2,
        overflow: TextOverflow.ellipsis,
      ),
    );
  }

  Widget _buildStocks() {
    return Opacity(
      opacity: isLocked ? 0.65 : 1.0,
      child: Wrap(
        spacing: 8,
        runSpacing: 6,
        children: news.coreStocksPreview.take(3).map((s) {
          return Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
            decoration: BoxDecoration(
              color: Colors.white.withOpacity(0.08),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Text(s.name, style: const TextStyle(color: Colors.white70, fontSize: 12)),
          );
        }).toList(),
      ),
    );
  }

  Widget _buildFooter() {
    return Opacity(
      opacity: isLocked ? 0.65 : 1.0,
      child: Row(
        children: [
          Text(news.sourceName, style: const TextStyle(color: Colors.white38, fontSize: 12)),
          const SizedBox(width: 8),
          Text(news.publishTime, style: const TextStyle(color: Colors.white24, fontSize: 12)),
        ],
      ),
    );
  }

  SectorChange _getChange(String sector) {
    return news.sectorChanges.firstWhere(
      (c) => c.name == sector,
      orElse: () => SectorChange(name: sector, publishValue: 0, currentValue: 0, change: 0),
    );
  }

  double _calcPct(SectorChange change) {
    return change.publishValue > 0 ? (change.change / change.publishValue * 100) : 0.0;
  }
}