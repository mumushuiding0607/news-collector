import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/providers/config_provider.dart';
import '../../data/models/news_item.dart';

/// 新闻评价属性展示组件
class NewsCardEvaluation extends ConsumerWidget {
  final NewsItem news;
  final bool isLocked;
  final bool showAll;
  final ThemeConfig? theme;

  const NewsCardEvaluation({
    super.key,
    required this.news,
    this.isLocked = false,
    this.showAll = false,
    this.theme,
  });

  bool get _hasEvaluation =>
      news.direction != null ||
      news.intensity != null ||
      news.expectedChange != null ||
      news.duration != null ||
      news.expectationLevel != null ||
      news.marketMode != null ||
      news.maxSectorRise != null;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final isDark = ref.watch(themeModeProvider) == AppThemeMode.dark;
    if (!_hasEvaluation) return const SizedBox.shrink();

    return Opacity(
      opacity: isLocked ? 0.65 : 1.0,
      child: showAll ? _buildFullPanel(isDark) : _buildCompactTags(isDark),
    );
  }

  /// 紧凑标签形式（用于卡片）
  Widget _buildCompactTags(bool isDark) {
    final tags = <Widget>[];

    // 方向
    if (news.direction != null) {
      tags.add(_buildDirectionTag(news.direction!));
    }

    // 强度
    if (news.intensity != null) {
      tags.add(_buildIntensityTag(news.intensity!, isDark));
    }

    // 最大涨幅
    if (news.maxSectorRise != null) {
      tags.add(_buildMaxRiseTag(news.maxSectorRise!));
    }

    if (tags.isEmpty) return const SizedBox.shrink();

    return Wrap(
      spacing: 6,
      runSpacing: 6,
      children: tags,
    );
  }

  /// 完整面板（用于详情弹窗）
  Widget _buildFullPanel(bool isDark) {
    final textMutedColor = isDark ? Colors.white38 : (theme?.textMutedColor ?? const Color(0xFF9B9B9B));
    final textColor = isDark ? Colors.white70 : (theme?.textSecondaryColor ?? const Color(0xFF5C5C5C));

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _buildInfoRow('方向', _getDirectionLabel(news.direction), Icon(_getDirectionIcon(news.direction), color: _getDirectionColor(news.direction), size: 16), textMutedColor, textColor),
        if (news.intensity != null) _buildInfoRow('强度', _getIntensityLabel(news.intensity!), _buildIntensityIndicator(news.intensity!, isDark), textMutedColor, textColor),
        if (news.expectedChange != null) _buildInfoRow('预期变化', news.expectedChange!, null, textMutedColor, textColor),
        if (news.duration != null) _buildInfoRow('持续时间', news.duration!, null, textMutedColor, textColor),
        if (news.expectationLevel != null) _buildInfoRow('预期程度', news.expectationLevel!, null, textMutedColor, textColor),
        if (news.marketMode != null) _buildInfoRow('市场模式', news.marketMode!, null, textMutedColor, textColor),
        if (news.maxSectorRise != null) _buildInfoRow('最大涨幅', '${news.maxSectorRise!.toStringAsFixed(2)}%', null, textMutedColor, textColor),
      ],
    );
  }

  Widget _buildInfoRow(String label, String value, Widget? trailing, Color labelColor, Color valueColor) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        children: [
          SizedBox(
            width: 72,
            child: Text(label, style: TextStyle(color: labelColor, fontSize: 13)),
          ),
          if (trailing != null) ...[
            trailing,
            const SizedBox(width: 8),
          ],
          Expanded(
            child: Text(
              value,
              style: TextStyle(color: valueColor, fontSize: 14, fontWeight: FontWeight.w500),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildDirectionTag(String direction) {
    final color = _getDirectionColor(direction);
    final icon = _getDirectionIcon(direction);
    final label = _getDirectionLabel(direction);

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: color.withOpacity(0.15),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withOpacity(0.3)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, color: color, size: 14),
          const SizedBox(width: 4),
          Text(label, style: TextStyle(color: color, fontSize: 12, fontWeight: FontWeight.w600)),
        ],
      ),
    );
  }

  Widget _buildIntensityTag(int intensity, bool isDark) {
    final bgColor = isDark ? Colors.white.withOpacity(0.08) : Colors.black.withOpacity(0.05);
    final textColor = isDark ? Colors.white70 : (theme?.textSecondaryColor ?? const Color(0xFF5C5C5C));
    final boltColor = isDark ? Colors.amber : const Color(0xFFE53935);

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: bgColor,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.bolt, color: boltColor, size: 14),
          const SizedBox(width: 4),
          Text(
            '强度 ${intensity.toString()}',
            style: TextStyle(color: textColor, fontSize: 12),
          ),
        ],
      ),
    );
  }

  Widget _buildMaxRiseTag(double maxRise) {
    final color = theme?.accentRedColor ?? const Color(0xFFE53935);

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: color.withOpacity(0.15),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withOpacity(0.3)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.trending_up, color: color, size: 14),
          const SizedBox(width: 4),
          Text(
            '${maxRise.toStringAsFixed(1)}%',
            style: TextStyle(color: color, fontSize: 12, fontWeight: FontWeight.w600),
          ),
        ],
      ),
    );
  }

  Widget _buildIntensityIndicator(int intensity, bool isDark) {
    final boltColor = isDark ? Colors.amber : const Color(0xFFE53935);
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: List.generate(5, (index) {
        final isFilled = index < intensity;
        return Container(
          width: 14,
          height: 6,
          margin: const EdgeInsets.only(right: 2),
          decoration: BoxDecoration(
            color: isFilled ? boltColor : (isDark ? Colors.white.withOpacity(0.2) : Colors.grey.withOpacity(0.2)),
            borderRadius: BorderRadius.circular(3),
          ),
        );
      }),
    );
  }

  IconData _getDirectionIcon(String? direction) {
    switch (direction?.toLowerCase()) {
      case '多头':
      case '上涨':
      case '看多':
        return Icons.trending_up;
      case '空头':
      case '下跌':
      case '看空':
        return Icons.trending_down;
      default:
        return Icons.trending_flat;
    }
  }

  String _getDirectionLabel(String? direction) {
    switch (direction?.toLowerCase()) {
      case '多头':
      case '上涨':
      case '看多':
        return '多头';
      case '空头':
      case '下跌':
      case '看空':
        return '空头';
      default:
        return direction ?? '中性';
    }
  }

  Color _getDirectionColor(String? direction) {
    switch (direction?.toLowerCase()) {
      case '多头':
      case '上涨':
      case '看多':
        return const Color(0xFFE53935);
      case '空头':
      case '下跌':
      case '看空':
        return const Color(0xFF43A047);
      default:
        return const Color(0xFF78909C);
    }
  }

  String _getIntensityLabel(int intensity) {
    return '$intensity 级';
  }
}