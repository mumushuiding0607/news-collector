import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/providers/config_provider.dart';
import '../../data/models/news_item.dart';
import '../../shared/widgets/score_badge.dart';
import 'news_card_evaluation.dart';

/// 新闻卡片主体内容
class NewsCardContent extends ConsumerWidget {
  final NewsItem news;
  final bool isLocked;
  final VoidCallback? onTap;

  const NewsCardContent({
    super.key,
    required this.news,
    this.isLocked = false,
    this.onTap,
  });

  bool get _isBearish {
    final d = news.direction?.toLowerCase();
    return d == '空头' || d == '下跌' || d == '看空' || d == '消极';
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = ref.watch(configProvider).theme;
    final bgColor = _isBearish ? theme.cardBackgroundBearishColor : theme.cardBackgroundColor;
    final borderColor = _isBearish ? theme.cardBorderBearishColor : theme.cardBorderColor;

    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [bgColor.withOpacity(0.4), bgColor.withOpacity(0.2)],
        ),
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: borderColor.withOpacity(0.5), width: 1),
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
                if (_hasEvaluation) ...[
                  const SizedBox(height: 12),
                  _buildEvaluation(),
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
    final index = news.sectorList.indexOf(sector);
    final rate = index >= 0 && index < news.currentChangeRateList.length ? news.currentChangeRateList[index] : 0;
    final isPositive = rate >= 0;
    final color = isPositive ? const Color(0xFFE53935) : const Color(0xFF43A047);

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
          Text('${rate.abs().toStringAsFixed(1)}%', style: TextStyle(color: color, fontSize: 14, fontWeight: FontWeight.bold)),
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

  bool get _hasEvaluation =>
      news.direction != null ||
      news.intensity != null ||
      news.expectedChange != null ||
      news.duration != null ||
      news.expectationLevel != null ||
      news.marketMode != null ||
      news.maxSectorRise != null;

  Widget _buildEvaluation() {
    return Opacity(
      opacity: isLocked ? 0.65 : 1.0,
      child: NewsCardEvaluation(news: news, isLocked: isLocked),
    );
  }

}