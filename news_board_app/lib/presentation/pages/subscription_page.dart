import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../core/providers/subscription_provider.dart';
import '../../core/providers/auth_provider.dart';
import '../../core/providers/config_provider.dart';
import '../widgets/subscription_plan_card.dart';
import '../widgets/payment_content.dart';
import '../widgets/confirm_payment_dialog.dart';
import '../widgets/payment_status_badge.dart';

class SubscriptionPage extends ConsumerStatefulWidget {
  const SubscriptionPage({super.key});

  @override
  ConsumerState<SubscriptionPage> createState() => _SubscriptionPageState();
}

class _SubscriptionPageState extends ConsumerState<SubscriptionPage> {
  String? _currentOrderNo;
  String? _currentPayMethod;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      // 订阅功能已禁用，跳转回首页
      final config = ref.read(configProvider);
      if (!config.features.subscriptionEnabled) {
        context.go('/');
        return;
      }
      ref.read(subscriptionProvider.notifier).loadPayMethod();
    });
  }

  @override
  Widget build(BuildContext context) {
    final config = ref.watch(configProvider);
    final authState = ref.watch(authProvider);
    final subState = ref.watch(subscriptionProvider);

    if (_currentOrderNo != null) {
      return _buildPaymentPage(context, subState);
    }

    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [Color(0xFF0D0D0D), Color(0xFF141414)],
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
                          return SubscriptionPlanCard(
                            plan: plan,
                            isCurrent: isCurrent,
                            onSubscribe: () => _subscribe(context, ref, plan.level),
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
    final config = ref.watch(configProvider);
    return Padding(
      padding: const EdgeInsets.all(20),
      child: Row(
        children: [
          IconButton(
            onPressed: () => context.go('/'),
            icon: const Icon(Icons.arrow_back, color: Colors.white),
          ),
          Expanded(
            child: Text(
              config.lock.subscriptionTitle,
              style: const TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.bold),
              textAlign: TextAlign.center,
            ),
          ),
          const SizedBox(width: 48),
        ],
      ),
    );
  }

  void _subscribe(BuildContext context, WidgetRef ref, String level) async {
    final orderResult = await ref.read(subscriptionProvider.notifier).createOrder(level);
    if (orderResult == null) {
      if (context.mounted) {
        final err = ref.read(subscriptionProvider).errorMessage;
        showDialog(
          context: context,
          builder: (ctx) => AlertDialog(
            content: Text(err ?? '创建订单失败'),
            actions: [
              TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('确定')),
            ],
          ),
        );
      }
      return;
    }

    final orderNo = orderResult['order_no'] as String;
    final status = orderResult['status'] as String;
    final payMethod = orderResult['pay_method'] as String;

    if (!context.mounted) return;

    setState(() {
      _currentOrderNo = orderNo;
      _currentPayMethod = payMethod;
    });

    if (status == 'mock') {
      await ref.read(subscriptionProvider.notifier).activateSubscription(level);
      if (context.mounted) {
        final uiTexts = ref.read(configProvider).uiTexts.subscription;
        showDialog(
          context: context,
          builder: (ctx) => AlertDialog(
            content: Text(uiTexts.success),
            actions: [
              TextButton(
                onPressed: () { Navigator.pop(ctx); context.go('/'); },
                child: const Text('确定'),
              ),
            ],
          ),
        );
      }
    }
  }

  Widget _buildPaymentPage(BuildContext context, SubscriptionState subState) {
    final uiTexts = ref.watch(configProvider).uiTexts.subscription;
    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [Color(0xFF0D0D0D), Color(0xFF141414)],
          ),
        ),
        child: SafeArea(
          child: Column(
            children: [
              _buildHeader(context),
              Expanded(
                child: SingleChildScrollView(
                  padding: const EdgeInsets.all(20),
                  child: Column(
                    children: [
                      const SizedBox(height: 20),
                      Text(
                        _getPayMethodTitle(uiTexts),
                        style: const TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        '订单号：$_currentOrderNo',
                        style: const TextStyle(color: Colors.white54, fontSize: 12),
                      ),
                      const SizedBox(height: 32),
                      PaymentContent(
                        payMethod: _currentPayMethod ?? '',
                        subState: subState,
                        onConfirmPayment: () => _showConfirmPaymentDialog(context),
                      ),
                      const SizedBox(height: 32),
                      PaymentStatusBadge(status: subState.currentOrderStatus ?? 'pending'),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  String _getPayMethodTitle(UiTextsSubscription uiTexts) {
    switch (_currentPayMethod) {
      case 'personal':
        return uiTexts.scanQrTitle;
      case 'wechat':
        return uiTexts.wechatQrTitle;
      default:
        return '订阅中...';
    }
  }

  void _showConfirmPaymentDialog(BuildContext context) {
    showDialog(
      context: context,
      builder: (ctx) => ConfirmPaymentDialog(
        onConfirm: (note) => _confirmPayment(context, note),
      ),
    );
  }

  Future<void> _confirmPayment(BuildContext context, String note) async {
    if (_currentOrderNo == null) return;

    final ok = await ref.read(subscriptionProvider.notifier).confirmPayment(_currentOrderNo!, note);
    if (!context.mounted) return;

    if (ok) {
      await ref.read(authProvider.notifier).refreshUser();
      if (context.mounted) context.go('/');
    } else {
      final err = ref.read(subscriptionProvider).errorMessage;
      showDialog(
        context: context,
        builder: (ctx) => AlertDialog(
          content: Text(err ?? '确认失败'),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('确定')),
          ],
        ),
      );
    }
  }
}