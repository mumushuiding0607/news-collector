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

  const SubscriptionState({
    this.level = SubscriptionLevel.free,
    this.expireAt,
    this.status = 'active',
    this.isLoading = false,
    this.errorMessage,
    this.plans = const [],
  });

  SubscriptionState copyWith({
    SubscriptionLevel? level,
    String? expireAt,
    String? status,
    bool? isLoading,
    String? errorMessage,
    List<SubscriptionPlan>? plans,
  }) {
    return SubscriptionState(
      level: level ?? this.level,
      expireAt: expireAt ?? this.expireAt,
      status: status ?? this.status,
      isLoading: isLoading ?? this.isLoading,
      errorMessage: errorMessage,
      plans: plans ?? this.plans,
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

  Future<bool> subscribe(String level) async {
    state = state.copyWith(isLoading: true, errorMessage: null);
    try {
      await _repo.subscribe(level);
      final newLevel = SubscriptionLevel.values.firstWhere(
        (e) => e.name == level,
        orElse: () => SubscriptionLevel.free,
      );
      state = state.copyWith(level: newLevel, isLoading: false);
      return true;
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        errorMessage: e.toString().replaceFirst('Exception: ', ''),
      );
      return false;
    }
  }

  Future<bool> cancel() async {
    state = state.copyWith(isLoading: true, errorMessage: null);
    try {
      await _repo.cancel();
      state = state.copyWith(level: SubscriptionLevel.free, isLoading: false);
      return true;
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        errorMessage: e.toString().replaceFirst('Exception: ', ''),
      );
      return false;
    }
  }
}

/// Provider
final subscriptionProvider = StateNotifierProvider<SubscriptionNotifier, SubscriptionState>((ref) {
  return SubscriptionNotifier();
});