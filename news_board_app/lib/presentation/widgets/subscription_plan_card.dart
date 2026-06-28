import 'package:flutter/material.dart';
import '../../core/providers/subscription_provider.dart';

class SubscriptionPlanCard extends StatelessWidget {
  final SubscriptionPlan plan;
  final bool isCurrent;
  final VoidCallback? onSubscribe;

  const SubscriptionPlanCard({
    super.key,
    required this.plan,
    required this.isCurrent,
    this.onSubscribe,
  });

  @override
  Widget build(BuildContext context) {
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
      child: InkWell(
        onTap: isCurrent || plan.price <= 0 ? null : onSubscribe,
        borderRadius: BorderRadius.circular(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _buildHeader(),
            const SizedBox(height: 8),
            _buildPrice(),
            const SizedBox(height: 12),
            ...plan.features.map(_buildFeature),
            const SizedBox(height: 16),
            _buildSubscribeButton(),
          ],
        ),
      ),
    );
  }

  Widget _buildHeader() {
    return Row(
      children: [
        Text(plan.name,
            style: const TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.bold)),
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

  Widget _buildPrice() {
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

  Widget _buildSubscribeButton() {
    return SizedBox(
      width: double.infinity,
      child: ElevatedButton(
        onPressed: isCurrent || plan.price <= 0 ? null : onSubscribe,
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
}