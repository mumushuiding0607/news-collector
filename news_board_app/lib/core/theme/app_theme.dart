import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../providers/config_provider.dart';

/// 动态主题 - 支持暗黑/明亮模式切换
class AppTheme {
  AppTheme._();

  static ThemeConfig of(BuildContext context) {
    return context.read(effectiveThemeConfigProvider);
  }

  static Color getScoreColor(BuildContext context, int score) {
    final theme = of(context);
    if (score >= 9) return theme.accentRedColor;
    if (score >= 7) return theme.accentGoldColor;
    return Colors.grey;
  }

  static Color getChangeColor(BuildContext context, double change) {
    final theme = of(context);
    if (change > 0) return theme.accentRedColor;
    if (change < 0) return theme.accentGreenColor;
    return theme.textMutedColor;
  }
}

/// 扩展 ConsumerWidget 便捷方法
extension ThemeExtension on Widget {
  ThemeConfig theme(BuildContext context) => AppTheme.of(context);
}