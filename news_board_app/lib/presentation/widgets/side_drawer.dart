import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../core/providers/auth_provider.dart';
import '../../core/providers/config_provider.dart';
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
    final uiTexts = config.uiTexts.sideDrawer;
    final features = config.features;

    Widget content = Container(
      padding: const EdgeInsets.all(24),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          _buildHandle(),
          const SizedBox(height: 24),
          _buildUserInfo(authState, uiTexts.freeUser, features.subscriptionEnabled),
          const SizedBox(height: 24),
          Expanded(
            child: ListView(
              controller: scrollController,
              shrinkWrap: true,
              children: [
                _buildMenuItem(context, Icons.summarize_outlined, uiTexts.briefing, () {
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
                _buildMenuItem(context, Icons.person_outline, uiTexts.accountManage, () {
                  Navigator.pop(context);
                  if (authState.isLoggedIn) {
                    context.go('/account');
                  } else {
                    context.go('/login');
                  }
                }),
                if (features.notificationsEnabled)
                  _buildMenuItem(context, Icons.notifications_outlined, uiTexts.notifications, () {}),
                _buildMenuItem(context, Icons.settings_outlined, uiTexts.settings, () {}),
                if (features.feedbackEnabled)
                  _buildMenuItem(context, Icons.feedback_outlined, uiTexts.feedback, () {
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

  Widget _buildHandle() {
    return Container(
      width: 40,
      height: 4,
      decoration: BoxDecoration(
        color: Colors.white24,
        borderRadius: BorderRadius.circular(2),
      ),
    );
  }

  Widget _buildUserInfo(AuthState authState, String freeUserText, bool subscriptionEnabled) {
    final email = authState.currentUser?.email ?? '游客';
    final displayText = email.length >= 3 ? email.substring(0, 3) : email;
    return Row(
      children: [
        CircleAvatar(
          radius: 28,
          backgroundColor: Colors.amber.shade700,
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
                style: const TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold),
                overflow: TextOverflow.ellipsis,
              ),
              if (subscriptionEnabled)
                Text(
                  authState.subscriptionLevel == 'free' ? freeUserText : '${authState.subscriptionLevel}会员',
                  style: const TextStyle(color: Colors.white54, fontSize: 14),
                ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildMenuItem(BuildContext context, IconData icon, String label, VoidCallback onTap) {
    return ListTile(
      leading: Icon(icon, color: Colors.white70, size: 22),
      title: Text(label, style: const TextStyle(color: Colors.white, fontSize: 15)),
      onTap: onTap,
      contentPadding: const EdgeInsets.only(left: 4, right: 8),
      visualDensity: VisualDensity.compact,
    );
  }
}