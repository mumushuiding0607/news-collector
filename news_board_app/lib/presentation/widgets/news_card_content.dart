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
    final theme = ref.watch(effectiveThemeProvider);
    final themeMode = ref.watch(themeModeProvider);
    final isDark = themeMode == AppThemeMode.dark;

    final bgColor = _isBearish ? theme.cardBackgroundBearishColor : theme.cardBackgroundColor;
    final borderColor = _isBearish ? theme.cardBorderBearishColor : theme.cardBorderColor;

    // 文字颜色：暗色模式用白色，亮色模式用主题色
    final textColor = isDark ? Colors.white : theme.textPrimaryColor;
    final textSecondaryColor = isDark ? Colors.white70 : theme.textSecondaryColor;
    final textMutedColor = isDark ? Colors.white38 : theme.textMutedColor;

    // 卡片渐变：暗色模式用透明底色渐变，亮色模式用纯白卡片+阴影
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
      decoration: isDark
          ? BoxDecoration(
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
            )
          : BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(24),
              border: Border.all(color: borderColor, width: 1),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withOpacity(0.06),
                  blurRadius: 20,
                  offset: const Offset(0, 4),
                ),
                BoxShadow(
                  color: Colors.black.withOpacity(0.04),
                  blurRadius: 40,
                  offset: const Offset(0, 12),
                ),
              ],
            ),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(24),
          splashColor: (isDark ? Colors.white : theme.textPrimaryColor).withOpacity(0.1),
          highlightColor: (isDark ? Colors.white : theme.textPrimaryColor).withOpacity(0.05),
          child: Padding(
            padding: const EdgeInsets.all(18),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _buildHeader(textColor),
                if (news.sectorList.isNotEmpty) ...[
                  const SizedBox(height: 14),
                  _buildSectors(theme, isDark),
                ],
                if (_hasEvaluation) ...[
                  const SizedBox(height: 12),
                  _buildEvaluation(theme, isDark),
                ],
                if (news.reason.isNotEmpty) ...[
                  const SizedBox(height: 12),
                  _buildReason(textSecondaryColor),
                ],
                if (news.coreStocksPreview.isNotEmpty) ...[
                  const SizedBox(height: 12),
                  _buildStocks(theme, isDark),
                ],
                const SizedBox(height: 12),
                _buildFooter(textMutedColor),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildHeader(Color textColor) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Expanded(
          child: Opacity(
            opacity: isLocked ? 0.65 : 1.0,
            child: Text(
              news.title,
              style: TextStyle(
                color: textColor,
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

  Widget _buildSectors(ThemeConfig theme, bool isDark) {
    return Opacity(
      opacity: isLocked ? 0.65 : 1.0,
      child: Wrap(
        spacing: 8,
        runSpacing: 8,
        children: news.sectorList.map((s) => _buildSectorTag(s, theme, isDark)).toList(),
      ),
    );
  }

  Widget _buildSectorTag(String sector, ThemeConfig theme, bool isDark) {
    final index = news.sectorList.indexOf(sector);
    final rate = index >= 0 && index < news.currentChangeRateList.length ? news.currentChangeRateList[index] : 0;
    final isPositive = rate >= 0;
    final color = isPositive ? theme.accentRedColor : theme.accentGreenColor;
    final tagBgColor = isDark ? color.withOpacity(0.15) : color.withOpacity(0.08);
    final tagBorderColor = isDark ? color.withOpacity(0.3) : color.withOpacity(0.2);
    final tagTextColor = isDark ? Colors.white70 : theme.textSecondaryColor;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: tagBgColor,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: tagBorderColor),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(sector, style: TextStyle(color: tagTextColor, fontSize: 13)),
          const SizedBox(width: 4),
          Icon(isPositive ? Icons.arrow_upward : Icons.arrow_downward, color: color, size: 16),
          Text('${rate.abs().toStringAsFixed(1)}%',
              style: TextStyle(color: color, fontSize: 14, fontWeight: FontWeight.bold)),
        ],
      ),
    );
  }

  Widget _buildReason(Color textColor) {
    return Opacity(
      opacity: isLocked ? 0.65 : 1.0,
      child: Text(
        news.reason,
        style: TextStyle(color: textColor, fontSize: 13, height: 1.4),
        maxLines: 2,
        overflow: TextOverflow.ellipsis,
      ),
    );
  }

  Widget _buildStocks(ThemeConfig theme, bool isDark) {
    final bgColor = isDark ? Colors.white.withOpacity(0.08) : theme.textPrimaryColor.withOpacity(0.05);
    final textColor = isDark ? Colors.white70 : theme.textSecondaryColor;

    return Opacity(
      opacity: isLocked ? 0.65 : 1.0,
      child: Wrap(
        spacing: 8,
        runSpacing: 6,
        children: news.coreStocksPreview.take(3).map((s) {
          return Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
            decoration: BoxDecoration(
              color: bgColor,
              borderRadius: BorderRadius.circular(12),
            ),
            child: Text(s.name, style: TextStyle(color: textColor, fontSize: 12)),
          );
        }).toList(),
      ),
    );
  }

  Widget _buildFooter(Color textColor) {
    return Opacity(
      opacity: isLocked ? 0.65 : 1.0,
      child: Row(
        children: [
          Text(news.sourceName, style: TextStyle(color: textColor, fontSize: 12)),
          const SizedBox(width: 8),
          Text(news.publishTime, style: TextStyle(color: textColor.withOpacity(0.7), fontSize: 12)),
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

  Widget _buildEvaluation(ThemeConfig theme, bool isDark) {
    return Opacity(
      opacity: isLocked ? 0.65 : 1.0,
      child: NewsCardEvaluation(news: news, isLocked: isLocked, theme: theme),
    );
  }
}