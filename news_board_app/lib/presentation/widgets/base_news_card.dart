import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/providers/config_provider.dart';

/// 新闻卡片基类容器（可复用外壳）
/// 所有新闻卡片（股市/AI/其他）都使用此容器样式
class BaseNewsCard extends ConsumerWidget {
  final Widget header;          // 标题行
  final List<Widget> body;      // 中间内容（可变）
  final Widget? footer;         // 底部（来源/时间）
  final bool isLocked;
  final VoidCallback? onTap;

  const BaseNewsCard({
    super.key,
    required this.header,
    this.body = const [],
    this.footer,
    this.isLocked = false,
    this.onTap,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = ref.watch(effectiveThemeProvider);
    final themeMode = ref.watch(themeModeProvider);
    final isDark = themeMode == AppThemeMode.dark;

    // 卡片背景：熊市用特殊色
    final bgColor = theme.cardBackgroundColor;
    final borderColor = theme.cardBorderColor;

    return Opacity(
      opacity: isLocked ? 0.65 : 1.0,
      child: Container(
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
                  BoxShadow(color: Colors.black.withOpacity(0.25), blurRadius: 20, offset: const Offset(0, 8)),
                ],
              )
            : BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(24),
                border: Border.all(color: borderColor, width: 1),
                boxShadow: [
                  BoxShadow(color: Colors.black.withOpacity(0.06), blurRadius: 20, offset: const Offset(0, 4)),
                  BoxShadow(color: Colors.black.withOpacity(0.04), blurRadius: 40, offset: const Offset(0, 12)),
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
                  header,
                  ...body,
                  if (footer != null) ...[
                    const SizedBox(height: 12),
                    footer!,
                  ],
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
