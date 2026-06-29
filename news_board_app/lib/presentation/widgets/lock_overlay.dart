import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../core/providers/config_provider.dart';

/// 锁定遮罩层（模糊 + 蒙版 + 订阅提示）
class LockOverlay extends ConsumerWidget {
  final bool isLoggedIn;
  final String lockTitle;
  final String lockButtonLoggedIn;
  final String lockButtonNotLoggedIn;

  const LockOverlay({
    super.key,
    required this.isLoggedIn,
    this.lockTitle = '订阅后可查看完整内容',
    this.lockButtonLoggedIn = '立即订阅',
    this.lockButtonNotLoggedIn = '登录后订阅',
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final themeMode = ref.watch(themeModeProvider);
    final isDark = themeMode == AppThemeMode.dark;

    // 浅色模式下使用灰色调
    final overlayColor = isDark ? Colors.black.withOpacity(0.2) : Colors.white.withOpacity(0.5);
    final iconColor = isDark ? Colors.white70 : Colors.grey[600];
    final textColor = isDark ? Colors.white70 : Colors.grey[700];

    return Positioned.fill(
      child: ClipRRect(
        borderRadius: BorderRadius.circular(24),
        child: BackdropFilter(
          filter: ImageFilter.blur(sigmaX: 2, sigmaY: 2),
          child: Container(
            margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
            decoration: BoxDecoration(
              color: overlayColor,
              borderRadius: BorderRadius.circular(24),
            ),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(Icons.lock_outline, color: iconColor, size: 36),
                const SizedBox(height: 8),
                Text(
                  lockTitle,
                  style: TextStyle(color: textColor, fontSize: 14),
                ),
                const SizedBox(height: 12),
                ElevatedButton(
                  onPressed: () => context.go(isLoggedIn ? '/subscribe' : '/login'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFFE53935),
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
                  ),
                  child: Text(
                    isLoggedIn ? lockButtonLoggedIn : lockButtonNotLoggedIn,
                    style: const TextStyle(fontWeight: FontWeight.bold),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}