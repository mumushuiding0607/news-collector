import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/providers/auth_provider.dart';

/// 侧边抽屉（用户信息页）
class SideDrawer extends ConsumerWidget {
  final ScrollController scrollController;

  const SideDrawer({super.key, required this.scrollController});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final authState = ref.watch(authProvider);

    return Container(
      padding: const EdgeInsets.all(24),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          _buildHandle(),
          const SizedBox(height: 24),
          _buildUserInfo(authState),
          const SizedBox(height: 24),
          Expanded(
            child: ListView(
              controller: scrollController,
              shrinkWrap: true,
              children: [
                _buildMenuItem(context, Icons.person_outline, '账号管理', () {}),
                _buildMenuItem(context, Icons.notifications_outlined, '消息通知', () {}),
                _buildMenuItem(context, Icons.settings_outlined, '系统设置', () {}),
                _buildMenuItem(context, Icons.feedback_outlined, '意见反馈', () {}),
              ],
            ),
          ),
          const SizedBox(height: 16),
          _buildLogoutButton(context, ref),
        ],
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

  Widget _buildUserInfo(AuthState authState) {
    return Row(
      children: [
        CircleAvatar(
          radius: 28,
          backgroundColor: Colors.amber.shade700,
          child: Text(
            (authState.currentUser?.phone ?? '游客').substring(0, 3),
            style: const TextStyle(color: Colors.white, fontSize: 16),
          ),
        ),
        const SizedBox(width: 16),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                authState.currentUser?.phone ?? '未登录',
                style: const TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold),
              ),
              Text(
                authState.subscriptionLevel == 'free' ? '免费用户' : '${authState.subscriptionLevel}会员',
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
      leading: Icon(icon, color: Colors.white70),
      title: Text(label, style: const TextStyle(color: Colors.white)),
      trailing: const Icon(Icons.chevron_right, color: Colors.white24),
      onTap: onTap,
      contentPadding: EdgeInsets.zero,
    );
  }

  Widget _buildLogoutButton(BuildContext context, WidgetRef ref) {
    return SizedBox(
      width: double.infinity,
      child: ElevatedButton(
        onPressed: () async {
          await ref.read(authProvider.notifier).logout();
          if (context.mounted) Navigator.pop(context);
        },
        style: ElevatedButton.styleFrom(
          backgroundColor: Colors.red.shade800,
          foregroundColor: Colors.white,
          padding: const EdgeInsets.symmetric(vertical: 14),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        ),
        child: const Text('退出登录', style: TextStyle(fontSize: 16)),
      ),
    );
  }
}