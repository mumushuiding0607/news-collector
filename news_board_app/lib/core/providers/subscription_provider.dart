import 'dart:typed_data';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../data/repositories/subscription_repository.dart';
import 'config_provider.dart';

/// 订阅等级
enum SubscriptionLevel { free, pro, premium }

/// 订阅计划（从 config API 获取，不再硬编码）
class SubscriptionPlan {
  final String level;
  final String name;
  final double price;
  final int durationDays;
  final String description;
  final List<String> features;

  const SubscriptionPlan({
    required this.level,
    required this.name,
    required this.price,
    required this.durationDays,
    required this.description,
    required this.features,
  });

  factory SubscriptionPlan.fromTier(SubscriptionTier tier) {
    return SubscriptionPlan(
      level: tier.level,
      name: tier.name,
      price: tier.price,
      durationDays: tier.durationDays,
      description: tier.description,
      features: tier.features,
    );
  }
}

/// 订阅状态
class SubscriptionState {
  final SubscriptionLevel level;
  final String? expireAt;
  final String status;
  final bool isLoading;
  final String? errorMessage;
  final List<SubscriptionPlan> plans;
  final String? currentOrderNo;
  final String? currentOrderStatus;
  final String? currentOrderCodeUrl;
  final String? currentPayMethod;
  final Uint8List? personalQrImageBytes;
  final bool paymentConfirmed;

  const SubscriptionState({
    this.level = SubscriptionLevel.free,
    this.expireAt,
    this.status = 'active',
    this.isLoading = false,
    this.errorMessage,
    this.plans = const [],
    this.currentOrderNo,
    this.currentOrderStatus,
    this.currentOrderCodeUrl,
    this.currentPayMethod,
    this.personalQrImageBytes,
    this.paymentConfirmed = false,
  });

  SubscriptionState copyWith({
    SubscriptionLevel? level,
    String? expireAt,
    String? status,
    bool? isLoading,
    String? errorMessage,
    List<SubscriptionPlan>? plans,
    String? currentOrderNo,
    String? currentOrderStatus,
    String? currentOrderCodeUrl,
    String? currentPayMethod,
    Uint8List? personalQrImageBytes,
    bool? paymentConfirmed,
  }) {
    return SubscriptionState(
      level: level ?? this.level,
      expireAt: expireAt ?? this.expireAt,
      status: status ?? this.status,
      isLoading: isLoading ?? this.isLoading,
      errorMessage: errorMessage,
      plans: plans ?? this.plans,
      currentOrderNo: currentOrderNo,
      currentOrderStatus: currentOrderStatus,
      currentOrderCodeUrl: currentOrderCodeUrl,
      currentPayMethod: currentPayMethod,
      personalQrImageBytes: personalQrImageBytes ?? this.personalQrImageBytes,
      paymentConfirmed: paymentConfirmed ?? this.paymentConfirmed,
    );
  }
}

/// Subscription Notifier
class SubscriptionNotifier extends StateNotifier<SubscriptionState> {
  final SubscriptionRepository _repo = SubscriptionRepository();

  SubscriptionNotifier() : super(const SubscriptionState()) {
    loadCurrent();
  }

  /// 从 ConfigProvider 获取套餐列表
  void setPlansFromConfig(List<SubscriptionTier> tiers) {
    state = state.copyWith(
      plans: tiers.map((t) => SubscriptionPlan.fromTier(t)).toList(),
    );
  }

  Future<void> loadCurrent() async {
    try {
      final data = await _repo.getCurrentSubscription();
      final levelStr = data['level'] as String? ?? 'free';
      final level = SubscriptionLevel.values.firstWhere(
        (e) => e.name == levelStr,
        orElse: () => SubscriptionLevel.free,
      );
      state = state.copyWith(
        level: level,
        expireAt: data['expire_at'] as String?,
        status: data['status'] as String? ?? 'active',
      );
    } catch (e) {
      // ignore
    }
  }

  /// 加载支付方式
  Future<void> loadPayMethod() async {
    try {
      final data = await _repo.getPayMethod();
      state = state.copyWith(currentPayMethod: data['pay_method'] as String?);
    } catch (e) {
      // ignore
    }
  }

  /// 创建订单，返回完整响应（含 pay_method / status / code_url 等）
  Future<Map<String, dynamic>?> createOrder(String level) async {
    state = state.copyWith(isLoading: true, errorMessage: null, paymentConfirmed: false);
    final data = await _repo.createOrder(level);
    final orderNo = data['order_no'] as String?;
    final codeUrl = data['code_url'] as String?;
    final h5Url = data['h5_url'] as String?;
    state = state.copyWith(
      isLoading: false,
      currentOrderNo: orderNo,
      currentOrderCodeUrl: codeUrl ?? h5Url,
      currentOrderStatus: data['status'] as String?,
      currentPayMethod: data['pay_method'] as String?,
    );

    // personal 模式：预加载收款码图片
    if (data['pay_method'] == 'personal') {
      await _loadPersonalQrImage();
    }

    return data;
  }

  Future<void> _loadPersonalQrImage() async {
    try {
      final bytes = await _repo.getPersonalQrImage();
      state = state.copyWith(personalQrImageBytes: bytes);
    } catch (e) {
      // ignore
    }
  }

  /// 用户确认已转账（personal 模式）
  Future<bool> confirmPayment(String orderNo, String note) async {
    state = state.copyWith(isLoading: true, errorMessage: null);
    await _repo.confirmPayment(orderNo, note);
    state = state.copyWith(isLoading: false, paymentConfirmed: true);
    return true;
  }

  /// 轮询订单状态（微信支付页面用）
  Future<String?> pollOrderStatus(String orderNo) async {
    try {
      final data = await _repo.getOrderStatus(orderNo);
      final status = data['status'] as String?;
      if (status == 'paid') {
        await loadCurrent();
        return 'paid';
      }
      state = state.copyWith(currentOrderStatus: status);
      return status;
    } catch (e) {
      return null;
    }
  }

  void clearCurrentOrder() {
    state = state.copyWith(
      currentOrderNo: null,
      currentOrderCodeUrl: null,
      currentOrderStatus: null,
      currentPayMethod: null,
      paymentConfirmed: false,
    );
  }

  /// 直接激活订阅（mock模式或测试用）
  Future<bool> activateSubscription(String level) async {
    await _repo.subscribe(level);
    final newLevel = SubscriptionLevel.values.firstWhere(
      (e) => e.name == level,
      orElse: () => SubscriptionLevel.free,
    );
    state = state.copyWith(level: newLevel, isLoading: false);
    clearCurrentOrder();
    return true;
  }
}

/// Provider
final subscriptionProvider = StateNotifierProvider<SubscriptionNotifier, SubscriptionState>((ref) {
  return SubscriptionNotifier();
});