import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../core/providers/auth_provider.dart';
import '../../core/providers/config_provider.dart';
import '../../core/providers/news_type_provider.dart';
import 'feedback_dialog.dart';
import 'summary_dialog.dart';

/// 侧边抽屉（用户信息页）
class SideDrawer extends ConsumerWidget {
  final ScrollController scrollController;

  const SideDrawer({super.key, required this.scrollController});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final authState = ref.watch(authProvider);
    final config = ref.watch(configProvider);
    final theme = ref.watch(effectiveThemeConfigProvider);
    final themeMode = ref.watch(themeModeProvider);
    final newsType = ref.watch(newsTypeProvider);
    final isDark = themeMode == AppThemeMode.dark;
    final uiTexts = config.uiTexts.sideDrawer;
    final features = config.features;

    // 颜色主题
    final handleColor = isDark ? Colors.white24 : Colors.black12;
    final avatarBgColor = isDark ? Colors.amber.shade700 : Colors.amber.shade600;
    final textPrimary = isDark ? Colors.white : theme.textPrimaryColor;
    final textSecondary = isDark ? Colors.white54 : theme.textSecondaryColor;
    final textMuted = isDark ? Colors.white38 : theme.textMutedColor;
    final menuIconColor = isDark ? Colors.white70 : theme.textSecondaryColor;
    final menuTextColor = isDark ? Colors.white : theme.textPrimaryColor;

    Widget content = Container(
      padding: const EdgeInsets.all(24),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          _buildHandle(handleColor),
          const SizedBox(height: 24),
          _buildUserInfo(authState, uiTexts.freeUser, features.subscriptionEnabled, avatarBgColor, textPrimary, textSecondary),
          const SizedBox(height: 24),
          Expanded(
            child: ListView(
              controller: scrollController,
              shrinkWrap: true,
              children: [
                _buildNewsTypeTree(context, ref, newsType, menuIconColor, menuTextColor, textMuted),
                const Divider(height: 1),
                _buildMenuItem(context, Icons.summarize_outlined, uiTexts.briefing, menuIconColor, menuTextColor, () {
                  Navigator.pop(context);
                  showGeneralDialog(
                    context: context,
                    barrierDismissible: true,
                    barrierLabel: '关闭',
                    barrierColor: Colors.black87,
                    transitionDuration: const Duration(milliseconds: 300),
                    pageBuilder: (_, __, ___) => const SummaryDialog(),
                  );
                }),
                _buildMenuItem(context, Icons.person_outline, uiTexts.accountManage, menuIconColor, menuTextColor, () {
                  Navigator.pop(context);
                  if (authState.isLoggedIn) {
                    context.go('/account');
                  } else {
                    context.go('/login');
                  }
                }),
                if (features.notificationsEnabled)
                  _buildMenuItem(context, Icons.notifications_outlined, uiTexts.notifications, menuIconColor, menuTextColor, () {}),
                _buildMenuItem(context, Icons.settings_outlined, uiTexts.settings, menuIconColor, menuTextColor, () {}),
                if (features.feedbackEnabled)
                  _buildMenuItem(context, Icons.feedback_outlined, uiTexts.feedback, menuIconColor, menuTextColor, () {
                    Navigator.pop(context);
                    showGeneralDialog(
                      context: context,
                      barrierDismissible: true,
                      barrierLabel: '关闭',
                      barrierColor: Colors.black87,
                      transitionDuration: const Duration(milliseconds: 300),
                      pageBuilder: (_, __, ___) => const FeedbackDialog(),
                    );
                  }),
              ],
            ),
          ),
          const SizedBox(height: 16),
          _buildBottomButton(context, ref, authState, uiTexts.logout),
        ],
      ),
    );

    // 未登录时添加透明遮罩，点击跳转登录页
    if (!authState.isLoggedIn) {
      content = GestureDetector(
        onTap: () {
          Navigator.pop(context);
          context.go('/login');
        },
        behavior: HitTestBehavior.opaque,
        child: content,
      );
    }

    return content;
  }

  Widget _buildBottomButton(BuildContext context, WidgetRef ref, AuthState authState, String logoutText) {
    if (!authState.isLoggedIn) {
      return SizedBox(
        width: double.infinity,
        child: ElevatedButton(
          onPressed: () {
            Navigator.pop(context);
            context.go('/login');
          },
          style: ElevatedButton.styleFrom(
            backgroundColor: Colors.amber.shade700,
            foregroundColor: Colors.white,
            padding: const EdgeInsets.symmetric(vertical: 14),
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          ),
          child: const Text('登录', style: TextStyle(fontSize: 16)),
        ),
      );
    }
    return SizedBox(
      width: double.infinity,
      child: ElevatedButton(
        onPressed: authState.isLoading ? null : () async {
          await ref.read(authProvider.notifier).logout();
          if (context.canPop()) context.pop();
        },
        style: ElevatedButton.styleFrom(
          backgroundColor: authState.isLoading ? Colors.grey : Colors.red.shade800,
          foregroundColor: Colors.white,
          padding: const EdgeInsets.symmetric(vertical: 14),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        ),
        child: authState.isLoading
            ? const SizedBox(
                width: 20,
                height: 20,
                child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
              )
            : Text(logoutText, style: const TextStyle(fontSize: 16)),
      ),
    );
  }

  Widget _buildHandle(Color color) {
    return Container(
      width: 40,
      height: 4,
      decoration: BoxDecoration(
        color: color,
        borderRadius: BorderRadius.circular(2),
      ),
    );
  }

  Widget _buildUserInfo(AuthState authState, String freeUserText, bool subscriptionEnabled, Color avatarBgColor, Color textPrimary, Color textSecondary) {
    final email = authState.currentUser?.email ?? '游客';
    final displayText = email.length >= 3 ? email.substring(0, 3) : email;
    return Row(
      children: [
        CircleAvatar(
          radius: 28,
          backgroundColor: avatarBgColor,
          child: Text(
            displayText,
            style: const TextStyle(color: Colors.white, fontSize: 16),
          ),
        ),
        const SizedBox(width: 16),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                email,
                style: TextStyle(color: textPrimary, fontSize: 18, fontWeight: FontWeight.bold),
                overflow: TextOverflow.ellipsis,
              ),
              if (subscriptionEnabled)
                Text(
                  authState.subscriptionLevel == 'free' ? freeUserText : '${authState.subscriptionLevel}会员',
                  style: TextStyle(color: textSecondary, fontSize: 14),
                ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildMenuItem(BuildContext context, IconData icon, String label, Color iconColor, Color textColor, VoidCallback onTap) {
    return ListTile(
      leading: Icon(icon, color: iconColor, size: 22),
      title: Text(label, style: TextStyle(color: textColor, fontSize: 15)),
      onTap: onTap,
      contentPadding: const EdgeInsets.only(left: 4, right: 8),
      visualDensity: VisualDensity.compact,
    );
  }

  Widget _buildNewsTypeTree(BuildContext context, WidgetRef ref, NewsType currentType, Color iconColor, Color textColor, Color textSecondary) {
    return Theme(
      data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
      child: ExpansionTile(
        leading: Icon(Icons.article_outlined, color: iconColor, size: 22),
        title: Text('新闻类型', style: TextStyle(color: textColor, fontSize: 15)),
        tilePadding: const EdgeInsets.only(left: 4, right: 8),
        childrenPadding: const EdgeInsets.only(left: 48),
        expandedAlignment: Alignment.centerLeft,
        children: [
          _buildTreeItem(
            context, ref,
            icon: Icons.show_chart,
            label: '股市新闻',
            selected: currentType == NewsType.stock,
            iconColor: Colors.green,
            onTap: () {
              if (currentType != NewsType.stock) {
                ref.read(newsTypeProvider.notifier).setNewsType(NewsType.stock);
              }
            },
            textColor: textColor,
            textSecondary: textSecondary,
          ),
          _buildTreeItem(
            context, ref,
            icon: Icons.smart_toy_outlined,
            label: 'AI新闻',
            selected: currentType == NewsType.ai,
            iconColor: Colors.purple,
            onTap: () {
              if (currentType != NewsType.ai) {
                ref.read(newsTypeProvider.notifier).setNewsType(NewsType.ai);
              }
            },
            textColor: textColor,
            textSecondary: textSecondary,
          ),
        ],
      ),
    );
  }

  Widget _buildTreeItem(
    BuildContext context,
    WidgetRef ref, {
    required IconData icon,
    required String label,
    required bool selected,
    required Color iconColor,
    required VoidCallback onTap,
    required Color textColor,
    required Color textSecondary,
  }) {
    return ListTile(
      leading: Icon(icon, color: selected ? iconColor : iconColor.withOpacity(0.5), size: 20),
      title: Text(
        label,
        style: TextStyle(
          color: selected ? textColor : textSecondary,
          fontSize: 14,
          fontWeight: selected ? FontWeight.w600 : FontWeight.normal,
        ),
      ),
      trailing: selected ? Icon(Icons.check, color: iconColor, size: 18) : null,
      onTap: onTap,
      contentPadding: const EdgeInsets.only(left: 4, right: 8),
      visualDensity: VisualDensity.compact,
    );
  }
}