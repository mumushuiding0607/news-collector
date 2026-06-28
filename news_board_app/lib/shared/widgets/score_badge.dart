import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/providers/config_provider.dart';

/// 分数徽章
class ScoreBadge extends ConsumerWidget {
  final int score;
  final double size;
  final bool isLocked;

  const ScoreBadge({
    super.key,
    required this.score,
    this.size = 40,
    this.isLocked = false,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = ref.watch(configProvider).theme;
    final color = _getScoreColor(theme, score);

    return Opacity(
      opacity: isLocked ? 0.15 : 1.0,
      child: Container(
        width: size,
        height: size,
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [color, color.withOpacity(0.7)],
          ),
          shape: BoxShape.circle,
          boxShadow: [
            BoxShadow(
              color: color.withOpacity(0.4),
              blurRadius: 12,
              offset: const Offset(0, 4),
            ),
          ],
        ),
        child: Center(
          child: Text(
            score.toString(),
            style: TextStyle(
              color: Colors.white,
              fontSize: size * 0.45,
              fontWeight: FontWeight.bold,
            ),
          ),
        ),
      ),
    );
  }

  Color _getScoreColor(ThemeConfig theme, int score) {
    if (score >= 9) return theme.accentRedColor;
    if (score >= 7) return theme.accentGoldColor;
    return Colors.grey;
  }
}