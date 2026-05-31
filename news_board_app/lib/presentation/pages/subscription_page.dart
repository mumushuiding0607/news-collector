import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../core/providers/subscription_provider.dart';
import '../../core/providers/auth_provider.dart';
import '../../core/providers/config_provider.dart';

class SubscriptionPage extends ConsumerWidget {
  const SubscriptionPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final config = ref.watch(configProvider);
    final authState = ref.watch(authProvider);
    final subState = ref.watch(subscriptionProvider);

    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [Color(0xFF0D0D0D), Color(0xFF121212)],
          ),
        ),
        child: SafeArea(
          child: Column(
            children: [
              _buildHeader(context),
              const SizedBox(height: 24),
              Expanded(
                child: config.subscriptionTiers.isEmpty
                    ? const Center(child: CircularProgressIndicator())
                    : ListView.builder(
                        padding: const EdgeInsets.symmetric(horizontal: 20),
                        itemCount: config.subscriptionTiers.length,
                        itemBuilder: (context, index) {
                          final tier = config.subscriptionTiers[index];
                          final plan = SubscriptionPlan.fromTier(tier);
                          final isCurrent = plan.level == authState.subscriptionLevel;

                          return Container(
                            margin: const EdgeInsets.only(bottom: 16),
                            padding: const EdgeInsets.all(20),
                            decoration: BoxDecoration(
                              gradient: LinearGradient(
                                begin: Alignment.topLeft,
                                end: Alignment.bottomRight,
                                colors: isCurrent
                                    ? [Colors.amber.withOpacity(0.2), Colors.amber.withOpacity(0.1)]
                                    : [Colors.white.withOpacity(0.08), Colors.white.withOpacity(0.04)],
                              ),
                              borderRadius: BorderRadius.circular(20),
                              border: Border.all(
                                color: isCurrent ? Colors.amber : Colors.white.withOpacity(0.12),
                                width: isCurrent ? 2 : 1,
                              ),
                            ),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                _buildPlanHeader(plan, isCurrent),
                                const SizedBox(height: 8),
                                _buildPrice(plan),
                                const SizedBox(height: 12),
                                ...plan.features.map((f) => _buildFeature(f)),
                                const SizedBox(height: 16),
                                _buildSubscribeButton(context, ref, plan, isCurrent),
                              ],
                            ),
                          );
                        },
                      ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildHeader(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(20),
      child: Row(
        children: [
          IconButton(
            onPressed: () => context.go('/'),
            icon: const Icon(Icons.arrow_back, color: Colors.white),
          ),
          const Expanded(
            child: Text(
              '订阅服务',
              style: TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.bold),
              textAlign: TextAlign.center,
            ),
          ),
          const SizedBox(width: 48),
        ],
      ),
    );
  }

  Widget _buildPlanHeader(SubscriptionPlan plan, bool isCurrent) {
    return Row(
      children: [
        Text(plan.name, style: const TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.bold)),
        if (isCurrent) ...[
          const SizedBox(width: 8),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
            decoration: BoxDecoration(color: Colors.amber, borderRadius: BorderRadius.circular(8)),
            child: const Text('当前', style: TextStyle(color: Colors.black, fontSize: 12)),
          ),
        ],
      ],
    );
  }

  Widget _buildPrice(SubscriptionPlan plan) {
    return Text(
      plan.price > 0 ? '¥${plan.price.toStringAsFixed(0)}' : '免费',
      style: TextStyle(color: Colors.amber.shade400, fontSize: 28, fontWeight: FontWeight.bold),
    );
  }

  Widget _buildFeature(String f) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: Row(
        children: [
          const Icon(Icons.check_circle, color: Colors.amber, size: 16),
          const SizedBox(width: 8),
          Text(f, style: const TextStyle(color: Colors.white70, fontSize: 14)),
        ],
      ),
    );
  }

  Widget _buildSubscribeButton(BuildContext context, WidgetRef ref, SubscriptionPlan plan, bool isCurrent) {
    return SizedBox(
      width: double.infinity,
      child: ElevatedButton(
        onPressed: isCurrent ? null : () => _subscribe(context, ref, plan.level),
        style: ElevatedButton.styleFrom(
          backgroundColor: isCurrent ? Colors.grey : Colors.amber.shade700,
          padding: const EdgeInsets.symmetric(vertical: 14),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        ),
        child: Text(
          isCurrent ? '当前方案' : '立即订阅',
          style: const TextStyle(color: Colors.black, fontWeight: FontWeight.bold),
        ),
      ),
    );
  }

  void _subscribe(BuildContext context, WidgetRef ref, String level) async {
    final ok = await ref.read(subscriptionProvider.notifier).subscribe(level);
    if (ok && context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('订阅成功！'), backgroundColor: Colors.green),
      );
      context.go('/');
    }
  }
}