import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/providers/config_provider.dart';
import '../../data/models/news_item.dart';
import 'base_news_card.dart';

/// AI 新闻卡片
class AiNewsCard extends ConsumerWidget {
  final AiNewsItem news;
  final bool isLocked;
  final VoidCallback? onTap;

  const AiNewsCard({
    super.key,
    required this.news,
    this.isLocked = false,
    this.onTap,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = ref.watch(effectiveThemeProvider);
    final themeMode = ref.watch(themeModeProvider);
    final isDark = themeMode == AppThemeMode.dark;

    final textColor = isDark ? Colors.white : theme.textPrimaryColor;
    final textSecondaryColor = isDark ? Colors.white70 : theme.textSecondaryColor;
    final textMutedColor = isDark ? Colors.white38 : theme.textMutedColor;

    return BaseNewsCard(
      isLocked: isLocked,
      onTap: onTap,
      header: _buildHeader(textColor),
      body: [
        if (news.domainList.isNotEmpty) ...[
          const SizedBox(height: 14),
          _buildDomains(theme, isDark),
        ],
        if (news.highlights.isNotEmpty) ...[
          const SizedBox(height: 12),
          _buildHighlights(textSecondaryColor, isDark),
        ],
        if (news.reason.isNotEmpty) ...[
          const SizedBox(height: 12),
          _buildReason(textSecondaryColor),
        ],
      ],
      footer: _buildFooter(textMutedColor),
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
        _buildScoreBadge(),
      ],
    );
  }

  Widget _buildScoreBadge() {
    if (isLocked) {
      return Container(
        width: 42,
        height: 42,
        decoration: BoxDecoration(
          color: Colors.grey.withOpacity(0.3),
          borderRadius: BorderRadius.circular(12),
        ),
        child: const Center(child: Icon(Icons.lock, color: Colors.white54, size: 20)),
      );
    }
    return Container(
      width: 42,
      height: 42,
      decoration: BoxDecoration(
        color: _scoreColor(news.score).withOpacity(0.15),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: _scoreColor(news.score).withOpacity(0.3)),
      ),
      child: Center(
        child: Text(
          news.score.toString(),
          style: TextStyle(
            color: _scoreColor(news.score),
            fontSize: 16,
            fontWeight: FontWeight.bold,
          ),
        ),
      ),
    );
  }

  Color _scoreColor(int score) {
    if (score >= 8) return Colors.red;
    if (score >= 6) return Colors.orange;
    return Colors.grey;
  }

  Widget _buildDomains(ThemeConfig theme, bool isDark) {
    return Opacity(
      opacity: isLocked ? 0.65 : 1.0,
      child: Wrap(
        spacing: 8,
        runSpacing: 8,
        children: news.domainList.map((d) => _buildDomainTag(d, theme, isDark)).toList(),
      ),
    );
  }

  Widget _buildDomainTag(String domain, ThemeConfig theme, bool isDark) {
    const color = Colors.purple;
    final bgColor = isDark ? color.withOpacity(0.2) : color.withOpacity(0.08);
    final borderColor = isDark ? color.withOpacity(0.4) : color.withOpacity(0.2);
    final textColor = isDark ? Colors.white70 : theme.textSecondaryColor;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: bgColor,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: borderColor),
      ),
      child: Text(domain, style: TextStyle(color: textColor, fontSize: 13)),
    );
  }

  Widget _buildHighlights(Color textColor, bool isDark) {
    return Opacity(
      opacity: isLocked ? 0.65 : 1.0,
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: isDark ? Colors.white.withOpacity(0.06) : Colors.amber.withOpacity(0.06),
          borderRadius: BorderRadius.circular(12),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('亮点', style: TextStyle(color: textColor, fontSize: 12, fontWeight: FontWeight.w600)),
            const SizedBox(height: 4),
            Text(
              news.highlights,
              style: TextStyle(color: textColor, fontSize: 13, height: 1.4),
              maxLines: 3,
              overflow: TextOverflow.ellipsis,
            ),
          ],
        ),
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
}
